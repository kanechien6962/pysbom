# PySBOM

PySBOM is a Python-based utility for managing, converting, and processing Software Bill of Materials (SBOM) data across different SPDX formats.

---

## 📁 Directory Structure

```text
pysbom/
├── main.py                  # Application entry point
├── main_window.py           # Main GUI window interface
├── form.py                  # Form layout and components
├── ini_form-editor.py       # INI form layout and components
├── build_exe.bat            # Executable build script
├── setup.bat                # Environment setup and dependency downloader
├── modify.png               # Reference image for code modifications
├── sbom/                    # Core SBOM module
│   ├── spdx3_converter.py   # SPDX v3 converter logic
│   └── sbom_exporter.py    # SBOM export utilities
├── tools/                   # External binaries/jar tools
│   └── spdx/                # SPDX Java tools (downloaded via setup.bat)
├── vendor/                  # Embedded runtime environments
│   └── runtime/             # OpenJDK 25 JRE (downloaded via setup.bat)
└── python-uswid/            # Sub-module for uSWID handling (cloned via setup.bat)
```

---

## ⚙️ Requirements

* **Operating System**: Windows 10/11 (64-bit)
* **Python**: Python 3.8 or higher
* **Java**: OpenJDK 25 (Managed automatically by `setup.bat`)
* **Git**: Required for cloning external repositories (`python-uswid`)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/kanechien6962/pysbom.git
cd pysbom
```

### 2. Run Setup Script

Before running or building the application, run `setup.bat` to automatically download and configure all external dependencies:
* **SPDX Java Tools** (`tools/spdx/tools-java-2.0.7-jar-with-dependencies.jar`)
* **OpenJDK 25 Runtime Environment** (`vendor/runtime/`)
* **python-uswid repository** (`python-uswid/`)

```cmd
setup.bat
```

### 3. Manual Configuration (Suggestion)

* Refer to `modify.png` if any manual code adjustments are required.

---

## 💻 Usage

### Running from Source

To start the graphical interface:

```bash
python main.py
```

### Building Executable

To package the project into a standalone executable:

```cmd
build_exe.bat
```

---

## 🔗 External Dependencies & Download Links

* **[SPDX Java Tools (v2.0.7)](https://github.com/spdx/tools-java/releases/download/v2.0.7/tools-java-2.0.7.zip)**: Java-based utilities for SPDX standard processing.
* **[Adoptium Temurin OpenJDK 25 JRE](https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/OpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip)**: Provides the Java runtime environment (`vendor/runtime/`). ([Download Page](https://adoptium.net/zh-CN/download?link=https%3A%2F%2Fgithub.com%2Fadoptium%2Ftemurin25-binaries%2Freleases%2Fdownload%2Fjdk-25.0.4.1%252B1%2FOpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip&vendor=Adoptium))
* **[python-uswid Repository](https://github.com/hughsie/python-uswid.git)**: Python library for handling ISO/IEC 19770-2 Software Identification (SWID) tags.
* **[SPDX Specification](https://github.com/spdx/spdx-spec.git)**: Official SPDX specification schema definitions.

---

## 📄 License

[Specify your license here, e.g., MIT License]