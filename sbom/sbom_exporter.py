
# sbom/sbom_exporter.py

from pathlib import Path

from .spdx3_converter import convert_spdx23_to_spdx301


def export_sbom(
    components,
    output_dir,
    cyclonedx_writer,
    spdx23_writer,
):
    """
    components:
        共用的元件資料集合

    cyclonedx_writer:
        既有 CycloneDX JSON 輸出函式

    spdx23_writer:
        既有 SPDX 2.3 JSON 輸出函式
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cyclonedx_path = output_dir / "bom.cyclonedx.json"
    spdx23_path = output_dir / "bom.spdx.json"
    spdx301_path = output_dir / "bom.spdx3.json"

    # 1. 保留現有 CycloneDX JSON 輸出
    cyclonedx_writer(components, cyclonedx_path)

    # 2. 先產生 SPDX 2.3 JSON
    spdx23_writer(components, spdx23_path)

    # 3. 將 SPDX 2.3 JSON 轉成 SPDX 3.0.1 JSON-LD
    convert_spdx23_to_spdx301(
        spdx23_path,
        spdx301_path,
    )

    return {
        "cyclonedx": cyclonedx_path,
        "spdx23": spdx23_path,
        "spdx301": spdx301_path,
    }
