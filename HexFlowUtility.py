import os
import sys
import json
import time
import warnings
import platform
from datetime import datetime

# Suppress urllib3 OpenSSL/LibreSSL warning BEFORE importing requests
warnings.filterwarnings('ignore', message='.*urllib3.*OpenSSL.*')
warnings.filterwarnings('ignore', message='.*NotOpenSSLWarning.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*urllib3.*')
try:
    import urllib3
    urllib3.disable_warnings()
    # Specifically disable NotOpenSSLWarning if it exists
    try:
        urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)
    except (AttributeError, NameError):
        pass
except ImportError:
    pass

import requests
import serial.tools.list_ports
from typing import Optional
import io
import contextlib

# Also suppress via requests (in case warnings were already emitted)
try:
    requests.packages.urllib3.disable_warnings()
except (AttributeError, ImportError):
    pass

from PySide6.QtCore import QProcess, Qt, Signal, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

 
def resource_path(filename):
    """Get the path to a resource file, handling both development and PyInstaller bundle modes."""
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # For one-file executables, data files are extracted to this temp directory
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        # Check in temp directory first (for one-file bundle)
        temp_path = os.path.join(base_path, filename)
        if os.path.exists(temp_path):
            return temp_path
        # Fallback to executable directory (for one-folder bundle)
        return os.path.join(os.path.dirname(sys.executable), filename)
    else:
        # Development mode - use script directory
        return os.path.join(os.path.dirname(__file__), filename)


BOOTLOADER_PATH = resource_path("bootloader.bin")
PARTITIONS_PATH = resource_path("partitions.bin")
DEFAULT_HOST = "hadasklugv2-dev.smartguest.ai"
FLASH_PASSWORD = "qwertyuiop"
CONFIG_FILE = resource_path("config.json")


def load_config() -> dict:
    """Load configuration from JSON file, return default if not exists."""
    default_config = {
        "host": DEFAULT_HOST
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure host is set, use default only if completely missing
                if "host" not in config or not config["host"]:
                    config["host"] = DEFAULT_HOST
                return config
        except Exception:
            return default_config
    return default_config


def save_config(config: dict) -> None:
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def get_api_url() -> str:
    """Get API URL from current configuration."""
    config = load_config()
    host = config.get("host", DEFAULT_HOST)
    
    # If host already includes protocol, use it as-is and append path
    if host.startswith("https://") or host.startswith("http://"):
        # Remove trailing slash if present
        host = host.rstrip("/")
        return f"{host}/webapp/devices/getFirmware"
    
    # Otherwise, default to https://
    return f"https://{host}/webapp/devices/getFirmware"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HexFlowUtility")
        self.resize(1100, 680)

        self.esptool_worker: Optional[EsptoolWorker] = None
        self.connected_port: Optional[str] = None
        self.downloaded_fw_path: Optional[str] = None
        self.serial_thread: Optional[SerialReader] = None
        self.auto_scroll_enabled: bool = True
        self.timestamp_enabled: bool = False

        self._build_ui()
        self._load_initial_state()

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        # Port and Firmware controls
        ports_group = QGroupBox()
        ports_layout = QGridLayout(ports_group)
        ports_layout.setHorizontalSpacing(8)
        ports_layout.setVerticalSpacing(8)

        ports_layout.addWidget(QLabel("Select Serial Port"), 0, 0, 1, 2)
        self.port_combo = QComboBox()
        self.port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ports_layout.addWidget(self.port_combo, 1, 0, 1, 1)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("↻")
        self.refresh_btn.setToolTip("Refresh ports")
        ports_layout.addWidget(self.refresh_btn, 1, 1)

        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.setCheckable(True)
        ports_layout.addWidget(self.connect_btn, 1, 2)

        ports_layout.addWidget(QLabel("Select Firmware"), 2, 0, 1, 2)
        self.fw_combo = QComboBox()
        ports_layout.addWidget(self.fw_combo, 3, 0, 1, 1)

        self.fw_browse_btn = QToolButton()
        self.fw_browse_btn.setText("⋯")
        self.fw_browse_btn.setToolTip("Browse local firmware file")
        ports_layout.addWidget(self.fw_browse_btn, 3, 1)

        self.host_settings_btn = QToolButton()
        self.host_settings_btn.setText("⚙")
        self.host_settings_btn.setToolTip("Change API host")
        ports_layout.addWidget(self.host_settings_btn, 3, 2)

        self.flash_btn = QPushButton("FLASH")
        # Set red background color for flash button with hover/pressed effects
        self.flash_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #dc3545;"
            "  color: white;"
            "  font-weight: bold;"
            "  border: none;"
            "  padding: 5px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #c82333;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #bd2130;"
            "}"
        )
        ports_layout.addWidget(self.flash_btn, 3, 3)

        self.erase_flash_btn = QPushButton("ERASE FLASH")
        # Set orange/red background color for erase flash button
        self.erase_flash_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #fd7e14;"
            "  color: white;"
            "  font-weight: bold;"
            "  border: none;"
            "  padding: 5px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #e86809;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #d65805;"
            "}"
        )
        ports_layout.addWidget(self.erase_flash_btn, 3, 4)

        root.addWidget(ports_group)

        # Console controls (above log box)
        console_bar = QHBoxLayout()
        self.console_input = QLineEdit()
        console_bar.addWidget(self.console_input, 1)
        self.console_send = QPushButton("SEND")
        console_bar.addWidget(self.console_send)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self.baud_combo.setCurrentText("115200")
        console_bar.addWidget(self.baud_combo)
        
        self.auto_scroll_btn = QPushButton("Auto Scroll")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.setToolTip("Automatically scroll to bottom when new messages arrive")
        console_bar.addWidget(self.auto_scroll_btn)
        
        self.timestamp_btn = QPushButton("Timestamp")
        self.timestamp_btn.setCheckable(True)
        self.timestamp_btn.setToolTip("Prepend timestamp to each log message")
        console_bar.addWidget(self.timestamp_btn)
        
        self.export_log_btn = QPushButton("Export")
        self.export_log_btn.setToolTip("Export logs to file")
        console_bar.addWidget(self.export_log_btn)
        
        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setToolTip("Clear the log output")
        console_bar.addWidget(self.clear_log_btn)

        root.addLayout(console_bar)

        # Serial output log box
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Set monospace font for better log readability
        font = QFont("Courier New", 14)
        font.setStyleHint(QFont.Monospace)
        # Try other common monospace fonts if Courier New isn't available
        if not font.exactMatch():
            font = QFont("Consolas", 14)
            font.setStyleHint(QFont.Monospace)
        if not font.exactMatch():
            font = QFont("Monaco", 14)
            font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(font)
        root.addWidget(self.log_text, 1)

        self.setCentralWidget(container)

        # Wiring
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.connect_btn.toggled.connect(self._toggle_connect)
        self.flash_btn.clicked.connect(self._on_flash)
        self.erase_flash_btn.clicked.connect(self._on_erase_flash)
        self.fw_browse_btn.clicked.connect(self._browse_firmware)
        self.host_settings_btn.clicked.connect(self._change_host)
        self.console_send.clicked.connect(self._send_console_input)
        self.console_input.returnPressed.connect(self._send_console_input)
        self.baud_combo.currentTextChanged.connect(self._maybe_restart_serial)
        self.auto_scroll_btn.toggled.connect(self._toggle_auto_scroll)
        self.timestamp_btn.toggled.connect(self._toggle_timestamp)
        self.export_log_btn.clicked.connect(self._export_log)
        self.clear_log_btn.clicked.connect(self._clear_log)

    def _load_initial_state(self) -> None:
        self._refresh_ports()
        config = load_config()
        current_host = config.get("host", DEFAULT_HOST)
        self._append_log(f"API Host: {current_host}\n")
        self._append_log(f"Bootloader path: {BOOTLOADER_PATH}\n")
        self._append_log(f"Partitions path: {PARTITIONS_PATH}\n")
        self._load_firmware_list()

    def _append_log(self, text: str) -> None:
        if self.timestamp_enabled:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
            text = f"[{timestamp}] {text}"
        # Use insertPlainText instead of append to avoid double newlines
        # and preserve exact formatting from serial data
        self.log_text.insertPlainText(text)
        
        if self.auto_scroll_enabled:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    # Serial ports
    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            self.port_combo.addItem(f"{p.device} - {p.description}", p.device)
        if not ports:
            self.port_combo.addItem("No ports found", "")

    def _toggle_connect(self, checked: bool) -> None:
        if checked:
            device = self.port_combo.currentData()
            if not device:
                QMessageBox.warning(self, "Serial", "No serial port selected")
                self.connect_btn.setChecked(False)
                return
            self.connected_port = device
            self.connect_btn.setText("DISCONNECT")
            self._append_log(f"Connected to {device}\n")
            self._start_serial_monitor()
        else:
            self._append_log("Disconnected\n")
            self._stop_serial_monitor()
            self.connected_port = None
            self.connect_btn.setText("CONNECT")

    # Firmware handling
    def _load_firmware_list(self) -> None:
        try:
            api_url = get_api_url()
            res = requests.get(api_url, timeout=15)
            res.raise_for_status()
            data = res.json()
            firmwares = data.get("firmware", [])
        except Exception as exc:
            self._append_log(f"Failed to fetch firmware list: {exc}\n")
            firmwares = []

        self.fw_combo.clear()
        for item in firmwares:
            name = f"{item.get('name','fw')} v{item.get('version','')}"
            self.fw_combo.addItem(name, item)
        if not firmwares:
            self.fw_combo.addItem("Browse local…", {})

    def _change_host(self) -> None:
        """Show dialog to change API host and save to config."""
        config = load_config()
        current_host = config.get("host", DEFAULT_HOST)
        
        new_host, ok = QInputDialog.getText(
            self,
            "Change API Host",
            f"Enter new API host (with https:// or http://):\nCurrent: {current_host}",
            text=current_host
        )
        
        if ok and new_host.strip():
            new_host = new_host.strip()
            # Remove trailing slash if present
            new_host = new_host.rstrip("/")
            
            # Validate URL format
            if new_host:
                # If user didn't include protocol, add https://
                if not new_host.startswith("https://") and not new_host.startswith("http://"):
                    new_host = f"https://{new_host}"
                
                config["host"] = new_host
                save_config(config)
                self._append_log(f"API Host changed to: {new_host}\n")
                self._load_firmware_list()  # Reload firmware list with new host

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select firmware (bin)", os.getcwd(), "BIN (*.bin)")
        if path:
            self.downloaded_fw_path = path
            base = os.path.basename(path)
            self._append_log(f"Selected local firmware: {base}\n")

    # Serial monitor control
    def _start_serial_monitor(self) -> None:
        if not self.connected_port:
            return
        self._stop_serial_monitor()
        baud = int(self.baud_combo.currentText())
        self.serial_thread = SerialReader(self.connected_port, baud)
        self.serial_thread.text_received.connect(self._append_log)
        self.serial_thread.error.connect(lambda m: self._append_log(f"[serial] {m}\n"))
        self.serial_thread.start()

    def _stop_serial_monitor(self) -> None:
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait(2000)  # Wait up to 2 seconds for thread to stop
            self.serial_thread = None
            # Give the OS time to release the serial port
            time.sleep(0.2)

    def _maybe_restart_serial(self) -> None:
        if self.connected_port:
            self._start_serial_monitor()

    def _send_console_input(self) -> None:
        if not self.serial_thread:
            return
        data = self.console_input.text()
        if not data:
            return
        # Append newline for convenience
        payload = (data + "\r\n").encode()
        self.serial_thread.write(payload)
        self.console_input.clear()

    def _toggle_auto_scroll(self, checked: bool) -> None:
        self.auto_scroll_enabled = checked

    def _toggle_timestamp(self, checked: bool) -> None:
        self.timestamp_enabled = checked

    def _export_log(self) -> None:
        """Export log content to a file with date/timestamp in filename."""
        log_content = self.log_text.toPlainText()
        
        if not log_content.strip():
            QMessageBox.information(self, "Export Log", "Log is empty. Nothing to export.")
            return
        
        # Generate filename with date and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"log_{timestamp}.log"
        
        # Get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            default_filename,
            "Log Files (*.log);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self._append_log(f"✅ Log exported to: {file_path}\n")
                QMessageBox.information(self, "Export Log", f"Log exported successfully to:\n{file_path}")
            except Exception as exc:
                self._append_log(f"❌ Failed to export log: {exc}\n")
                QMessageBox.critical(self, "Export Failed", f"Failed to export log:\n{exc}")

    def _clear_log(self) -> None:
        self.log_text.clear()

    def _ensure_firmware_file(self) -> Optional[str]:
        if self.downloaded_fw_path and os.path.exists(self.downloaded_fw_path):
            return self.downloaded_fw_path

        item = self.fw_combo.currentData()
        if not isinstance(item, dict) or not item.get("url"):
            return None
 
        url = item["url"]
        filename = os.path.basename(url)
        self._append_log(f"Downloading firmware: {url}\n")
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(filename, "wb") as f:
                f.write(r.content)
            self._append_log(f"Saved firmware to {filename}\n")
            self.downloaded_fw_path = os.path.abspath(filename)
            return self.downloaded_fw_path
        except Exception as exc:
            QMessageBox.critical(self, "Download failed", str(exc))
        return None
 
    # Flashing
    def _on_flash(self) -> None:
        if not self.connected_port:
            QMessageBox.warning(self, "Flash", "Please connect to a serial port first")
            return
        if not os.path.exists(BOOTLOADER_PATH) or not os.path.exists(PARTITIONS_PATH):
            QMessageBox.critical(self, "Missing files", "bootloader.bin or partitions.bin not found next to app")
            return
        firmware_path = self._ensure_firmware_file()
        if not firmware_path:
            QMessageBox.warning(self, "Flash", "Select or download a firmware first")
            return
        
        # Password prompt before flashing
        password, ok = QInputDialog.getText(
            self, 
            "Flash Firmware - Password Required",
            "Enter password to flash firmware:",
            echo=QLineEdit.EchoMode.Password
        )
        
        if not ok:
            # User cancelled
            return
        
        if password != FLASH_PASSWORD:
            self._append_log("❌ Flash cancelled: Incorrect password.\n")
            return
 
        # Pause serial monitor while flashing and focus the flash log
        self._stop_serial_monitor()
        self.log_text.setFocus()

        # Build esptool arguments (without "python -m esptool" prefix)
        esptool_args = [
            "--chip", "esp32",
            "--port", self.connected_port,
            "--baud", "460800",
            "write_flash", "-z",
            "--flash_mode", "dio",
            "--flash_freq", "40m",
            "--flash_size", "4MB",
            "0x1000", BOOTLOADER_PATH,
            "0x8000", PARTITIONS_PATH,
            "0x10000", firmware_path,
        ]

        self._append_log("Starting flash…\n")
        self.flash_btn.setEnabled(False)
        self.erase_flash_btn.setEnabled(False)  # Disable erase while flashing

        # Use EsptoolWorker to run esptool directly (works in both dev and bundled mode)
        self.esptool_worker = EsptoolWorker(esptool_args)
        self.esptool_worker.output_received.connect(self._append_log)
        self.esptool_worker.finished_signal.connect(self._flash_finished)
        self.esptool_worker.start()

    def _flash_finished(self, code: int) -> None:
        self.flash_btn.setEnabled(True)
        self.erase_flash_btn.setEnabled(True)  # Re-enable erase after flashing
        if code == 0:
            self._append_log("✅ Flash complete.\n")
        else:
            self._append_log(f"❌ Flash failed with code {code}\n")
        # Clean up worker
        if self.esptool_worker:
            self.esptool_worker.deleteLater()
            self.esptool_worker = None
        # Resume serial monitor if still connected
        if self.connected_port:
            self._start_serial_monitor()

    def _on_erase_flash(self) -> None:
        """Erase the flash memory using esptool."""
        if not self.connected_port:
            QMessageBox.warning(self, "Erase Flash", "Please connect to a serial port first")
            return
        
        # Check if flash or erase is already running
        if self.esptool_worker and self.esptool_worker.isRunning():
            QMessageBox.warning(self, "Erase Flash", "Another operation is already in progress")
            return
        
        # Confirm erase operation
        reply = QMessageBox.question(
            self,
            "Erase Flash",
            "⚠️ WARNING: This will erase ALL data from the flash memory!\n\nAre you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Password prompt before erasing
        password, ok = QInputDialog.getText(
            self, 
            "Erase Flash - Password Required",
            "Enter password to erase flash:",
            echo=QLineEdit.EchoMode.Password
        )
        
        if not ok:
            # User cancelled
            return
        
        if password != FLASH_PASSWORD:
            self._append_log("❌ Erase flash cancelled: Incorrect password.\n")
            return
        
        # Pause serial monitor while erasing
        self._stop_serial_monitor()
        self.log_text.setFocus()
        
        # Build esptool arguments (without "python -m esptool" prefix)
        esptool_args = [
            "--chip", "esp32",
            "--port", self.connected_port,
            "erase_flash",
        ]
        
        self._append_log("Starting flash erase…\n")
        self.erase_flash_btn.setEnabled(False)
        self.flash_btn.setEnabled(False)  # Disable flash while erasing
        
        # Use EsptoolWorker to run esptool directly (works in both dev and bundled mode)
        self.esptool_worker = EsptoolWorker(esptool_args)
        self.esptool_worker.output_received.connect(self._append_log)
        self.esptool_worker.finished_signal.connect(self._erase_flash_finished)
        self.esptool_worker.start()

    def _erase_flash_finished(self, code: int) -> None:
        self.erase_flash_btn.setEnabled(True)
        self.flash_btn.setEnabled(True)  # Re-enable flash after erasing
        if code == 0:
            self._append_log("✅ Flash erase complete.\n")
        else:
            self._append_log(f"❌ Flash erase failed with code {code}\n")
        # Clean up worker
        if self.esptool_worker:
            self.esptool_worker.deleteLater()
            self.esptool_worker = None
        # Resume serial monitor if still connected
        if self.connected_port:
            self._start_serial_monitor()


class EsptoolWorker(QThread):
    """Worker thread to run esptool commands without subprocess"""
    output_received = Signal(str)
    finished_signal = Signal(int)  # exit code
    
    def __init__(self, args_list: list) -> None:
        super().__init__()
        self.args_list = args_list
    
    def run(self) -> None:
        try:
            import esptool
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Save original sys.argv
            original_argv = sys.argv
            
            try:
                # Set sys.argv to esptool arguments (skip "python -m esptool" part)
                sys.argv = ['esptool'] + self.args_list
                
                exit_code = 0
                # Redirect stdout and stderr
                with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                    try:
                        esptool.main()
                    except SystemExit as e:
                        exit_code = e.code if e.code is not None else 0
                
                # Emit captured output
                stdout_text = stdout_capture.getvalue()
                stderr_text = stderr_capture.getvalue()
                
                if stdout_text:
                    self.output_received.emit(stdout_text)
                if stderr_text:
                    self.output_received.emit(stderr_text)
                
                self.finished_signal.emit(exit_code)
                
            finally:
                # Restore original sys.argv
                sys.argv = original_argv
                
        except Exception as exc:
            self.output_received.emit(f"\n❌ Esptool error: {exc}\n")
            self.finished_signal.emit(1)


class SerialReader(QThread):
    text_received = Signal(str)
    error = Signal(str)

    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self._port = port
        self._baud = baudrate
        self._running = True
        self._ser: Optional[serial.Serial] = None
        self._buffer = bytearray()

    def run(self) -> None:
        try:
            self._ser = serial.Serial(self._port, self._baud, timeout=0.2)
        except Exception as exc:
            self.error.emit(f"Open failed on {self._port}: {exc}")
            return
        try:
            last_flush_time = time.time()
            while self._running:
                try:
                    if self._ser.in_waiting:
                        # Read available data
                        new_data = self._ser.read(self._ser.in_waiting)
                        if new_data:
                            self._buffer.extend(new_data)
                            last_flush_time = time.time()
                            
                            # Process buffered data looking for complete lines
                            while True:
                                # Try to find line breaks
                                newline_idx = -1
                                for idx, byte in enumerate(self._buffer):
                                    if byte in (10, 13):  # \n or \r
                                        newline_idx = idx
                                        break
                                
                                if newline_idx >= 0:
                                    # Found a line break, decode up to and including it
                                    line_bytes = self._buffer[:newline_idx + 1]
                                    self._buffer = self._buffer[newline_idx + 1:]
                                    
                                    try:
                                        text = line_bytes.decode('utf-8', errors='replace')
                                        self.text_received.emit(text)
                                    except Exception:
                                        # Fallback to latin-1 if UTF-8 fails
                                        text = line_bytes.decode('latin-1', errors='replace')
                                        self.text_received.emit(text)
                                else:
                                    # No line break found
                                    # Flush if buffer is large (reduced threshold)
                                    if len(self._buffer) > 256:
                                        chunk = bytes(self._buffer)
                                        self._buffer.clear()
                                        try:
                                            text = chunk.decode('utf-8', errors='replace')
                                            self.text_received.emit(text)
                                        except Exception:
                                            text = chunk.decode('latin-1', errors='replace')
                                            self.text_received.emit(text)
                                    break
                    else:
                        # No data available, check if we should flush buffer due to timeout
                        current_time = time.time()
                        if self._buffer and (current_time - last_flush_time) > 0.1:  # 100ms timeout
                            # Flush any pending data
                            chunk = bytes(self._buffer)
                            self._buffer.clear()
                            try:
                                text = chunk.decode('utf-8', errors='replace')
                                if text:
                                    self.text_received.emit(text)
                            except Exception:
                                text = chunk.decode('latin-1', errors='replace')
                                if text:
                                    self.text_received.emit(text)
                            last_flush_time = current_time
                except Exception as exc:
                    self.error.emit(f"Read error: {exc}")
                    self.msleep(100)
                self.msleep(10)  # Reduced sleep time for more responsive updates
            
            # Flush any remaining buffer on exit
            if self._buffer:
                try:
                    text = bytes(self._buffer).decode('utf-8', errors='replace')
                    if text:
                        self.text_received.emit(text)
                except Exception:
                    pass
        finally:
            try:
                if self._ser and self._ser.is_open:
                    self._ser.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False

    def write(self, data: bytes) -> None:
        try:
            if self._ser and self._ser.is_open:
                self._ser.write(data)
        except Exception as exc:
            self.error.emit(f"Write error: {exc}")


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

 
if __name__ == "__main__":
    main()
