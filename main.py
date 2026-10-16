import sys
from pathlib import Path

# Allow running directly from the source tree without first installing python-uswid.
# The bundled uswid package lives in ./python-uswid/uswid.
PROJECT_DIR = Path(__file__).resolve().parent
USWID_SOURCE_DIR = PROJECT_DIR / "python-uswid"
if (USWID_SOURCE_DIR / "uswid" / "__init__.py").is_file():
    sys.path.insert(0, str(USWID_SOURCE_DIR))

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Ili SBOM Generator")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
