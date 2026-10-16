from __future__ import annotations

import os
import sys
import json
from pathlib import Path

# 匯入 PyQt6 GUI 相關元件與事件處理類別
from PyQt6.QtGui import QCloseEvent, QFont, QKeySequence, QShortcut, QIcon
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QPlainTextEdit

# 匯入 uswid 庫及其支援的各式 SBOM / 韌體格式處理類別
from uswid import __version__ as uswid_version
from uswid.format_coswid import uSwidFormatCoswid
from uswid.format_cyclonedx import uSwidFormatCycloneDX
from uswid.format_goswid import uSwidFormatGoswid
from uswid.format_ini import uSwidFormatIni
from uswid.format_pe import uSwidFormatPe
from uswid.format_spdx import uSwidFormatSpdx
from uswid.format_swid import uSwidFormatSwid
from uswid.format_uswid import uSwidFormatUswid

# 匯入由 Qt Designer 所產生的 UI 介面類別
from form import Ui_MainWindow

from sbom.spdx3_converter import (
    OUTPUT_FORMAT as SPDX3_OUTPUT_FORMAT,
    OUTPUT_FORMATS as SPDX3_OUTPUT_FORMATS,
    convert_spdx23_to_spdx301
)

# ==============================================================================
# 全域轉換配置 (可透過修改此處數字切換工具的輸入與輸出格式)
# ==============================================================================
# 輸入格式編號：1=INI, 2=CycloneDX, 3=SPDX, 4=SWID XML, 5=CoSWID, 6=PE
INPUT_FORMAT = 1
# OUTPUT_FORMAT 1 或 2 都會同時輸出三種格式：
# CycloneDX JSON + SPDX 2.3 JSON + SPDX 3.0.1 JSON-LD。
# 其他數值仍保留原本單一格式輸出模式。
OUTPUT_FORMAT = 1
MULTI_OUTPUT_FORMATS = (1, 2)

# 輸入格式對照表：編號 -> (格式名稱, 處理類別, 檔案篩選器, 是否為二進位檔)
INPUT_FORMATS = {
    1: ("INI", uSwidFormatIni, "INI files (*.ini)", False),
    2: ("CycloneDX JSON",uSwidFormatCycloneDX,"CycloneDX JSON (*.bom.json *.cdx.json)",False),
    3: ("SPDX JSON", uSwidFormatSpdx, "SPDX JSON (*.spdx.json)", False),
    4: ("SWID XML", uSwidFormatSwid, "SWID XML (*.swid.xml *.xml)", False),
    5: ("CoSWID", uSwidFormatCoswid, "CoSWID (*.coswid *.cbor)", True),
    6: ("EFI / PE binary", uSwidFormatPe, "EFI / PE (*.efi *.exe *.o)", True),
}
# 輸出格式對照表：編號 -> (格式名稱, 處理類別, 檔案副檔名, 檔案篩選器, 預覽模式[json/text/binary])
OUTPUT_FORMATS = {
    1: ("CycloneDX JSON",uSwidFormatCycloneDX,".cdx.json","CycloneDX JSON (*.cdx.json *.bom.json)","json"),
    2: ("SPDX JSON",uSwidFormatSpdx,".spdx.json","SPDX JSON (*.spdx.json)","json"),
    3: ("EFI / PE binary",uSwidFormatPe,".efi","EFI / PE (*.efi *.exe *.o)","binary"),
    4: ("uSWID binary",uSwidFormatUswid,".uswid","uSWID (*.uswid *.raw *.bin)","binary"),
    5: ("CoSWID",uSwidFormatCoswid,".coswid","CoSWID (*.coswid *.cbor)","binary"),
    6: ("INI", uSwidFormatIni, ".ini", "INI files (*.ini)", "text"),
    7: ("SWID XML", uSwidFormatSwid, ".xml", "SWID XML (*.xml)", "text"),
    8: ("GoSWID JSON", uSwidFormatGoswid, ".json", "JSON (*.json)", "json"),
}

# 檢查設定的格式編號是否合法
if INPUT_FORMAT not in INPUT_FORMATS:
    raise ValueError(f"Unsupported INPUT_FORMAT: {INPUT_FORMAT}")
if OUTPUT_FORMAT not in OUTPUT_FORMATS:
    raise ValueError(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")
# 解析目前專案的目錄路徑
PROJECT_DIR = Path(__file__).resolve().parent
# 解構提取當前選擇的輸入與輸出格式設定資訊
INPUT_NAME, INPUT_CLASS, INPUT_FILTER, INPUT_BINARY = INPUT_FORMATS[INPUT_FORMAT]
OUTPUT_NAME, OUTPUT_CLASS, OUTPUT_SUFFIX, OUTPUT_FILTER, OUTPUT_PREVIEW = (OUTPUT_FORMATS[OUTPUT_FORMAT])
# 定義應用程式視窗標題
if OUTPUT_FORMAT in MULTI_OUTPUT_FORMATS:
    APP_TITLE = f"Ili SBOM Generator, {INPUT_NAME} to CycloneDX + SPDX 2.3 + SPDX 3.0.1"
else:
    APP_TITLE = f"Ili SBOM Generator, {INPUT_NAME} to {OUTPUT_NAME}"

# ─── Install ─────────────────────────────────────────────
def resource_path(relative_path):
    """PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

# ==============================================================================
# 主視窗類別定義
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.setWindowIcon(QIcon(resource_path("sbom_48x48.ico")))
        self.ui.setupUi(self)# 初始化 Qt Designer 產生的 UI 佈局
        self.ini_path: Path | None = None # 記錄目前載入的輸入檔案路徑
        self.output_path: Path | None = None # 記錄輸出檔案路徑
        self.spdx2_output_path: Path | None = None # 記錄 SPDX 2.3 輸出檔案路徑
        self.spdx3_output_path: Path | None = None # 記錄 SPDX 3.0.1 輸出檔案路徑

        # 動態根據當前選擇的輸入/輸出格式，更新 GUI 上的按鈕與分頁文字
        self.ui.loadButton.setText(f"Load {INPUT_NAME}")
        self.ui.saveButton.setText(f"Save {INPUT_NAME}")
        self.ui.pathLabel.setText(f"No {INPUT_NAME} file loaded")
        self.ui.iniEditor.setPlaceholderText(
            f"Load a {INPUT_NAME} file to edit its contents here."
        )
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.iniTab), f"{INPUT_NAME} Editor"
        )
        self.ui.jsonPreview.setPlaceholderText(
            f"Generated {OUTPUT_NAME} will appear here."
        )
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.jsonTab), f"{OUTPUT_NAME} Preview"
        )
        self.ui.spdx3JsonPreview.setPlaceholderText(
            "Generated SPDX 3.0.1 JSON-LD will appear here."
        )
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.spdx3JsonTab), "SPDX 3.0.1 JSON Preview"
        )

        # 設定預覽與 Log 視窗使用等寬字型 (Consolas)，並關閉自動換行 (INI 表單編輯器自行處理)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        for editor in (self.ui.jsonPreview, self.ui.spdx3JsonPreview, self.ui.logView):
            editor.setFont(mono)
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # 初始化控制元件狀態 (未載入檔案前停用儲存與生成按鈕)
        self.ui.saveButton.setEnabled(False)
        self.ui.generateButton.setEnabled(False)
        self.ui.generateButton.setText("Generate")
        self.statusBar().showMessage("Ready")
        self.update_title(False)

        # 綁定按鈕點擊與編輯器變更訊號 (Signals & Slots)
        self.ui.loadButton.clicked.connect(self.load_ini)
        self.ui.saveButton.clicked.connect(self.save_ini_as)
        self.ui.generateButton.clicked.connect(self.generate_json)
        self.ui.iniEditor.modificationChanged.connect(self.update_title)

        # 設定全域快捷鍵：Ctrl+O 載入、Ctrl+S 儲存
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.load_ini)
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_current_ini)

    def update_title(self, modified: bool = False) -> None:
        """更新視窗標題，若檔案有修改則在標題後方加上星號 (*)"""
        self.setWindowTitle(APP_TITLE + (" *" if modified else ""))

    def append_log(self, text: str) -> None:
        """在 Log 檢視區域新增一行訊息"""
        if cleaned := text.rstrip():
            self.ui.logView.appendPlainText(cleaned)

    @staticmethod
    def read_text_file(path: Path) -> str:
        """嘗試多種常見編碼 (UTF-8 with BOM, UTF-8, CP950/繁體中文) 讀取文字檔"""
        data = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "cp950"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                pass
        raise UnicodeDecodeError("unknown", data, 0, len(data), "Unsupported encoding")

    def load_ini(self) -> None:
        """載入輸入檔案的處理邏輯"""
        if not self.confirm_discard_changes(): # 若有未儲存變更，先詢問使用者
            return
        initial_dir = str(self.ini_path.parent if self.ini_path else PROJECT_DIR.parent)
        filename, _ = QFileDialog.getOpenFileName(self,f"Load {INPUT_NAME}",initial_dir,f"{INPUT_FILTER};;All files (*)")

        if not filename:
            return
        path = Path(filename)
        try:
            if INPUT_BINARY:
                # 若為二進位檔，只讀取資訊不顯示完整內容
                text = f"Binary input: {path.name}\nSize: {path.stat().st_size} bytes"
            else:
                # 若為文字檔，讀取內容以供編輯
                text = self.read_text_file(path)
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(self, "Load failed", str(error))
            return

        # 更新狀態與 UI 顯示
        self.ini_path = path
        self.output_path = None
        self.spdx2_output_path = None
        self.spdx3_output_path = None
        self.ui.iniEditor.setReadOnly(INPUT_BINARY) # 二進位檔設為唯讀
        # INI 輸入以表單顯示；其他格式/二進位資訊，或解析失敗時退回純文字檢視
        as_form = self.ui.iniEditor.setPlainText(
            text, structured=(INPUT_FORMAT == 1 and not INPUT_BINARY)
        )
        self.ui.iniEditor.setModified(False)
        if INPUT_FORMAT == 1 and not INPUT_BINARY and not as_form:
            self.append_log("INI 無法解析為欄位，已改用 Raw text 檢視。")
        self.ui.jsonPreview.clear()
        self.ui.spdx3JsonPreview.clear()
        self.ui.pathLabel.setText(str(path))
        self.ui.saveButton.setEnabled(not INPUT_BINARY)# 二進位檔停用儲存按鈕
        self.ui.generateButton.setEnabled(True)
        self.update_title(False)
        self.statusBar().showMessage(f"Loaded {path.name}")
        self.append_log(f"Loaded: {path}")

    def write_ini(self, path: Path) -> bool:
        """將編輯器中的內容寫入檔案"""
        if INPUT_BINARY:
            return True
        try:
            path.write_text(self.ui.iniEditor.toPlainText(), encoding="utf-8", newline="\n")
        except OSError as error:
            QMessageBox.critical(self, "Save failed", str(error))
            return False
        self.ini_path = path
        self.ui.iniEditor.setModified(False)
        self.ui.pathLabel.setText(str(path))
        self.ui.saveButton.setEnabled(True)
        self.ui.generateButton.setEnabled(True)
        self.update_title(False)
        self.append_log(f"Saved: {path}")
        return True

    def save_current_ini(self) -> bool:
        """儲存目前檔案（若為新檔則觸發「另存新檔」）"""
        if INPUT_BINARY:
            return self.ini_path is not None
        if self.ini_path is None:
            return self.save_ini_as()
        return self.write_ini(self.ini_path)

    def save_ini_as(self) -> bool:
        """另存新檔對話框邏輯"""
        if INPUT_BINARY:
            return False
        initial = self.ini_path or (PROJECT_DIR / "TconFirmware.input")
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Save {INPUT_NAME}", str(initial), INPUT_FILTER
        )
        return bool(filename) and self.write_ini(Path(filename))

    def default_output_path(self) -> Path:
        """根據輸入檔名自動推算預設的輸出檔案路徑與副檔名"""
        assert self.ini_path is not None
        name = self.ini_path.name
        known_suffixes = (
            ".spdx.json", ".cdx.json", ".bom.json", ".swid.xml", ".coswid",
            ".cbor", ".uswid", ".raw", ".bin", ".ini", ".xml", ".json",
            ".efi", ".exe", ".o",
        )
        for suffix in known_suffixes:
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]
                break
        suffix = ".cdx.json" if OUTPUT_FORMAT in MULTI_OUTPUT_FORMATS else OUTPUT_SUFFIX
        return self.ini_path.with_name(name + suffix)

    def generate_json(self) -> None:
        """核心轉換邏輯：讀取輸入檔、解析 SBOM 資料結構並轉換導出為目標格式"""
        if self.ini_path is None:
            self.load_ini()
            if self.ini_path is None:
                return
        if not INPUT_BINARY and not self.save_current_ini():
            return
        # 跳出另存對話框選擇輸出路徑
        multi_output = OUTPUT_FORMAT in MULTI_OUTPUT_FORMATS
        dialog_name = "CycloneDX + SPDX 2.3 + SPDX 3.0.1" if multi_output else OUTPUT_NAME
        dialog_filter = "CycloneDX JSON (*.cdx.json *.bom.json)" if multi_output else OUTPUT_FILTER
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Generate {dialog_name}", str(self.output_path or self.default_output_path()), dialog_filter
        )
        if not filename:
            return
        output_path = Path(filename)
        primary_suffix = ".cdx.json" if multi_output else OUTPUT_SUFFIX
        if not output_path.name.lower().endswith(primary_suffix):
            output_path = output_path.with_name(output_path.name + primary_suffix)

        self.output_path = output_path
        self.spdx2_output_path = None
        self.spdx3_output_path = None
        self.ui.jsonPreview.clear()
        self.ui.spdx3JsonPreview.clear()
        self.ui.logView.clear()
        self.append_log(f"Input : {self.ini_path}")
        self.append_log(f"Output: {output_path}")
        if multi_output:
            self.append_log(f"Format: {INPUT_NAME} -> CycloneDX JSON + SPDX 2.3 JSON + SPDX 3.0.1 JSON-LD")
        else:
            self.append_log(f"Format: {INPUT_NAME} -> {OUTPUT_NAME}")
        self.append_log(f"uSWID: {uswid_version}")
        self.set_busy(True)
        try:
            assert self.ini_path is not None
            # 1. 實例化輸入格式解析器並載入資料到通用容器 (container)
            input_formatter = INPUT_CLASS()
            container = input_formatter.load(self.ini_path.read_bytes(), path=str(self.ini_path))
            # 2. 處理輸出邏輯 (針對 PE 執行檔格式特別處理，其餘使用標準物件)
            if multi_output:
                # 同一份通用 SBOM container 分別序列化，避免 SPDX 轉換結果取代 CycloneDX。
                cyclonedx_blob = uSwidFormatCycloneDX().save(container)
                spdx2_blob = uSwidFormatSpdx().save(container)

                output_path.write_bytes(cyclonedx_blob)
                self.spdx2_output_path = output_path.with_name(
                    output_path.name[: -len(primary_suffix)] + ".spdx.json"
                )

                self.spdx2_output_path.write_bytes(spdx2_blob)

                spdx3_suffix = SPDX3_OUTPUT_FORMATS[SPDX3_OUTPUT_FORMAT][1]
                self.spdx3_output_path = output_path.with_name(
                    output_path.name[: -len(primary_suffix)] + spdx3_suffix
                )

                convert_spdx23_to_spdx301(
                    self.spdx2_output_path,
                    self.spdx3_output_path,
                )

                self.append_log(f"CycloneDX: {output_path}")
                self.append_log(f"SPDX 2.3: {self.spdx2_output_path}")
                self.append_log(f"SPDX 3.0.1: {self.spdx3_output_path}")
            else:
                if OUTPUT_FORMAT == 3:
                    if not output_path.exists():
                        raise ValueError("PE output requires an existing PE/EFI file with a .sbom section.")
                    output_formatter = uSwidFormatPe(filepath=str(output_path))
                else:
                    output_formatter = OUTPUT_CLASS()
                output_blob = output_formatter.save(container)
                output_path.write_bytes(output_blob)

                if OUTPUT_FORMAT == 2:
                    spdx3_suffix = SPDX3_OUTPUT_FORMATS[SPDX3_OUTPUT_FORMAT][1]
                    self.spdx3_output_path = output_path.with_name(
                        output_path.name[: -len(OUTPUT_SUFFIX)] + spdx3_suffix
                    )

                    convert_spdx23_to_spdx301(
                        output_path,
                        self.spdx3_output_path,
                    )

                    self.append_log(f"SPDX 3.0.1: {self.spdx3_output_path}")

        except Exception as error:
            self.append_log(f"Generation failed: {error}")
            self.statusBar().showMessage("Generation failed")
            QMessageBox.critical(self, "Generation failed", str(error))
            return
        finally:
            self.set_busy(False)
        self.generation_finished()

    def set_busy(self, busy: bool) -> None:
        """控制轉檔期間按鈕的啟用/停用狀態與文字換算"""
        self.ui.loadButton.setEnabled(not busy)
        self.ui.saveButton.setEnabled(
            not busy and self.ini_path is not None and not INPUT_BINARY
        )
        self.ui.generateButton.setEnabled(not busy and self.ini_path is not None)
        self.ui.generateButton.setText("Generating..." if busy else "Generate")
        if busy:
            self.statusBar().showMessage(f"Generating {OUTPUT_NAME}...")

    def generation_finished(self) -> None:
        """轉換完成後的預覽呈現與通知對話框"""
        assert self.output_path is not None
        try:
            blob = self.output_path.read_bytes()
            # 依據格式類別呈現預覽：JSON 自動排版、文字直接顯示、二進位顯示大小
            if OUTPUT_PREVIEW == "json":
                preview = json.dumps(json.loads(blob.decode("utf-8")), indent=2, ensure_ascii=False)
            elif OUTPUT_PREVIEW == "text":
                preview = blob.decode("utf-8", errors="replace")
            else:
                preview = f"Binary output: {self.output_path.name}\nSize: {len(blob)} bytes"
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            QMessageBox.warning(self, "Output problem", str(error))
            return
        self.ui.jsonPreview.setPlainText(preview)
        if self.spdx2_output_path is not None:
            self.append_log(f"SPDX 2.3: {self.spdx2_output_path}")
        if self.spdx3_output_path is not None:
            try:
                spdx3_blob = self.spdx3_output_path.read_bytes()
                spdx3_preview = json.dumps(
                    json.loads(spdx3_blob.decode("utf-8")),
                    indent=2,
                    ensure_ascii=False,
                )
                self.ui.spdx3JsonPreview.setPlainText(spdx3_preview)
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                QMessageBox.warning(self, "SPDX 3.0.1 output problem", str(error))
                return
        self.append_log("Generation completed successfully.")
        self.statusBar().showMessage(f"Generated {self.output_path.name}")
        generated_files = str(self.output_path)
        if self.spdx2_output_path is not None:
            generated_files += f"\n{self.spdx2_output_path}"
        if self.spdx3_output_path is not None:
            generated_files += f"\n{self.spdx3_output_path}"
        output_label = "CycloneDX JSON + SPDX 2.3 JSON + SPDX 3.0.1 JSON-LD" if OUTPUT_FORMAT in MULTI_OUTPUT_FORMATS else OUTPUT_NAME
        QMessageBox.information(
            self,
            "Generation completed",
            f"{output_label} generated successfully:\n{generated_files}",
        )

    def confirm_discard_changes(self) -> bool:
        """檢查是否有未儲存的變更，跳出對話框詢問使用者要「儲存」、「放棄」或「取消」"""
        if not self.ui.iniEditor.isModified():
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_current_ini()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        """攔截視窗關閉事件，確認未儲存的資料是否處理"""
        event.accept() if self.confirm_discard_changes() else event.ignore()
