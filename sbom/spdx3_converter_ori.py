
# sbom/spdx3_converter.py

import json
import subprocess
from pathlib import Path


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

BUNDLED_JAVA = PROJECT_ROOT / "runtime" / "bin" / "java.exe"

if BUNDLED_JAVA.is_file():
    JAVA_EXECUTABLE = str(BUNDLED_JAVA)
else:
    JAVA_EXECUTABLE = "java"

SPDX_JAR = (
    PROJECT_ROOT
    / "tools"
    / "spdx"
    / "tools-java-2.0.7-jar-with-dependencies.jar"
)

def convert_spdx23_to_spdx301(
    input_json,
    output_jsonld,
    java_executable="java",
):
    """
    Convert SPDX 2.3 JSON into SPDX 3.0.1 JSON-LD.

    Returns the output file path.
    """
    input_path = Path(input_json).resolve()
    output_path = Path(output_jsonld).resolve()

    if not Path(SPDX_JAR).is_file():
        raise SPDXConversionError(
            "SPDX Java JAR not found: {}".format(SPDX_JAR)
        )

    if not input_path.is_file():
        raise SPDXConversionError(
            "Input SPDX file not found: {}".format(input_path)
        )

    # Verify the source is actually an SPDX 2.3 JSON document.
    try:
        with input_path.open("r", encoding="utf-8") as file:
            document = json.load(file)
    except (ValueError, OSError) as exc:
        raise SPDXConversionError(
            "Cannot read input SPDX JSON: {}".format(exc)
        ) from exc

    if document.get("spdxVersion") != "SPDX-2.3":
        raise SPDXConversionError(
            "Expected spdxVersion SPDX-2.3; got {!r}".format(
                document.get("spdxVersion")
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        java_executable,
        "-jar",
        str(SPDX_JAR),
        "Convert",
        str(input_path),
        str(output_path),
        "JSON",
        "JSONLD",
    ]

    # Do not leave a stale output looking like a successful conversion.
    if output_path.exists():
        output_path.unlink()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SPDXConversionError(
            "Java executable not found. Check JDK and PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SPDXConversionError(
            "SPDX Java conversion timed out."
        ) from exc

    if result.returncode != 0:
        raise SPDXConversionError(
            "SPDX Java conversion failed.\n"
            "Exit code: {}\n"
            "STDOUT:\n{}\n"
            "STDERR:\n{}".format(
                result.returncode,
                result.stdout,
                result.stderr,
            )
        )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise SPDXConversionError(
            "Java exited successfully but output is missing or empty."
        )

    # Confirm that the result is valid JSON syntax.
    try:
        with output_path.open("r", encoding="utf-8") as file:
            json.load(file)
    except (ValueError, OSError) as exc:
        raise SPDXConversionError(
            "Output is not valid JSON-LD JSON: {}".format(exc)
        ) from exc

    return output_path
