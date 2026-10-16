
import json
import subprocess
import sys
from pathlib import Path


# Select the converter formats here.  The numeric style matches main_window.py.
INPUT_FORMAT = 1
OUTPUT_FORMAT = 1

INPUT_FORMATS = {
    1: ("SPDX 2.3 JSON", ".spdx.json"),
}
OUTPUT_FORMATS = {
    1: ("SPDX 3.0 JSON-LD", ".spdx3.json", False),
    2: ("SPDX 3.0 Canonical JSON", ".spdx3.canonical.json", True),
}

if INPUT_FORMAT not in INPUT_FORMATS:
    raise ValueError(f"Unsupported INPUT_FORMAT: {INPUT_FORMAT}")
if OUTPUT_FORMAT not in OUTPUT_FORMATS:
    raise ValueError(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")

if getattr(sys, "frozen", False):
    # 打包後：以 EXE 所在目錄為基準
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    # 開發時：以本 Python 檔案所在目錄為基準
    APP_ROOT = Path(__file__).resolve().parent.parent


SPDX_JAR = (
    APP_ROOT
    / "tools"
    / "spdx"
    / "tools-java-2.0.7-jar-with-dependencies.jar"
)

BUNDLED_JAVA = APP_ROOT / "runtime" / "bin" / "java.exe"


def get_java_executable():
    """優先使用隨程式附帶的 Java Runtime。"""
    if BUNDLED_JAVA.is_file():
        return str(BUNDLED_JAVA)

    # 開發環境可使用系統已安裝的 Java。
    return "java"


def convert_spdx23_to_spdx301(input_path, output_path):
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    """
    Convert SPDX 2.3 JSON into SPDX 3.0.1 JSON-LD.

    Returns the output file path.
    """
    if not SPDX_JAR.is_file():
        raise FileNotFoundError(
            "SPDX Java JAR not found: {}".format(SPDX_JAR)
        )

    if not input_path.is_file():
        raise FileNotFoundError(
            "SPDX input file not found: {}".format(input_path)
        )

    with input_path.open("r", encoding="utf-8") as file:
        source = json.load(file)

    if source.get("spdxVersion") != "SPDX-2.3":
        raise ValueError("Input is not SPDX-2.3 JSON.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        output_path.unlink()

    java_executable = get_java_executable()

    command = [
        java_executable,
        "-jar",
        str(SPDX_JAR),
        "Convert",
        str(input_path),
        str(output_path),
        "JSON",
        "JSONLD",
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=180,
            check=False,
            cwd=str(APP_ROOT),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Java not found. Check bundled runtime or system PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("SPDX conversion timed out.") from exc

    if result.returncode != 0:
        raise RuntimeError(
            "SPDX conversion failed.\n"
            "Exit code: {}\n"
            "STDOUT:\n{}\n"
            "STDERR:\n{}".format(
                result.returncode,
                result.stdout,
                result.stderr,
            )
        )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("SPDX output is missing or empty.")

    with output_path.open("r", encoding="utf-8") as file:
        json.load(file)

    return output_path
