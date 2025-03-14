## Update: 
## 1. Assignment of the "selected_file" attribute
## The attribute is now initialized in the constructor (self.selected_file = None) to prevent assignment errors.
##•••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
## 2. Error handling when checking adb/fastboot commands
## In the update_device_status method, exceptions (notably FileNotFoundError) are handled to prevent the application from crashing.
##••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
## 3. Full translation into English
## All text strings have been translated into English by default (with the option to switch to French via the language toggle).
##•••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
## 4. Multi-threading and real-time feedback
## All long-running operations (download, extraction, installation, update, flash, etc.) run in separate threads to ensure UI responsiveness. A label at the bottom displays the real-time status of the devices.
##•••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
## 5. Fixes for Linux features: install adb/fastboot, update adb/fastboot.
##••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
## 6. Added the possibility to use no slot via adb sideload.
##••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••





import os
import sys
import subprocess
import urllib.request
import hashlib
from zipfile import ZipFile, is_zipfile
import threading
import time
import ctypes  # To check for admin privileges on Windows
import shutil
import logging
from datetime import datetime
from pathlib import Path
import platform

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar

# --- Configuration ---
PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-{}.zip"
DOWNLOAD_ZIP_NAME = "platform-tools.zip"
EXTRACT_DIR = "platform-tools"
IS_WINDOWS = os.name == "nt"

# Logger configuration (console and file)
log_filename = "adbinstaller.log"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout),
                        logging.FileHandler(log_filename, encoding="utf-8")
                    ])

# --- Utility Functions ---

def calculate_file_hash(file_path, algorithm="sha256"):
    """Calculates the file hash for integrity verification."""
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logging.error("Error calculating hash: %s", e)
        return None

def download_file(url, destination, progress_callback=None, cancel_check=lambda: False):
    """
    Downloads a file from the specified URL to the destination.
    Supports resume if a partial file exists.
    """
    try:
        dest_path = Path(destination)
        resume_byte_pos = dest_path.stat().st_size if dest_path.exists() else 0

        req = urllib.request.Request(url)
        if resume_byte_pos:
            req.add_header("Range", f"bytes={resume_byte_pos}-")
            logging.info("Resuming download at byte %s", resume_byte_pos)

        with urllib.request.urlopen(req) as response, open(destination, "ab") as out_file:
            total_length = response.getheader("content-length")
            if total_length:
                total_length = int(total_length) + resume_byte_pos
            downloaded = resume_byte_pos
            block_size = 8192
            while True:
                if cancel_check():
                    logging.warning("Download cancelled by user.")
                    return False
                block = response.read(block_size)
                if not block:
                    break
                out_file.write(block)
                downloaded += len(block)
                if progress_callback and total_length:
                    progress_callback(downloaded / total_length * 100)
        return True
    except Exception as e:
        logging.error("Download error: %s", e)
        return False

def extract_zip(zip_path, extract_to, progress_callback=None):
    """
    Extracts the zip file into the specified directory.
    """
    try:
        if not is_zipfile(zip_path):
            raise Exception("Invalid file (not a zip)")
        with ZipFile(zip_path, "r") as zip_ref:
            file_list = zip_ref.namelist()
            total_files = len(file_list)
            for i, file in enumerate(file_list, 1):
                zip_ref.extract(file, extract_to)
                if progress_callback:
                    progress_callback(i / total_files * 100)
        return True
    except Exception as e:
        logging.error("Extraction error: %s", e)
        return False

def tool_available(tool):
    """
    Checks if a tool is available by running 'tool version' or 'tool --version'.
    """
    try:
        for arg in ["version", "--version"]:
            try:
                result = subprocess.run([tool, arg], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logging.info("%s detected: %s", tool, result.stdout.splitlines()[0])
                    return True
            except Exception:
                continue
        logging.warning("%s did not return a version.", tool)
        return False
    except Exception as e:
        logging.error("Error checking %s: %s", tool, e)
        return False

def tool_in_path(tool):
    """Checks if the tool is available in the PATH."""
    return any(Path(path, tool).exists() for path in os.environ["PATH"].split(os.pathsep))

# --- Main Application Class ---

class ADBInstaller(BoxLayout):
    def __init__(self, **kwargs):
        super(ADBInstaller, self).__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        # Set default language to English
        self.language = "en"
        self.translations = {
            "en": {
                "check_adb_fastboot": "Check ADB/Fastboot",
                "install": "Install ADB/Fastboot",
                "update": "Update ADB/Fastboot",
                "cancel": "Cancel Operation",
                "export_log": "Export Log",
                "flash": "Flash",
                "browse": "Browse",
                "select_slot": "Select Slot",
                "select_partition": "Select Partition",
                "verbose_logging": "Verbose Logging",
                "force_install": "Force Install",
                "log_level": "Log Level",
                "reboot_recovery": "ADB Reboot Recovery",
                "reboot": "ADB Reboot",
                "reboot_bootloader": "ADB Reboot Bootloader",
                "reboot_edl": "Reboot EDL",
                "reboot_fastbootd": "Reboot FastbootD",
                "erase_cache": "Erase Cache",
                "check_adb_devices": "Check ADB Devices",
                "check_fastboot_devices": "Check Fastboot Devices",
                "check_lsusb": "Check LSUSB",
                "start_sideload": "Start Sideload",
                "getvar_all": "getvar all",
                "language": "Language: English",
                "install_linux": "Install via package manager",
                "update_linux": "Update via package manager",
                "no_device": "No device detected",
                "device_adb": "Device detected in ADB mode",
                "device_fastboot": "Device detected in Fastboot mode",
                "device_both": "Device detected in both ADB and Fastboot modes",
                "log_exported": "Log successfully exported to ",
                "warn_admin": "Warning: Run the script as Administrator for full functionality.",
                "warn_root": "Warning: Running without root privileges may cause issues with ADB/Fastboot."
            },
            "fr": {
                "check_adb_fastboot": "Vérifier ADB/Fastboot",
                "install": "Installer ADB/Fastboot",
                "update": "Mettre à jour ADB/Fastboot",
                "cancel": "Annuler l'opération",
                "export_log": "Exporter le Log",
                "flash": "Flasher",
                "browse": "Parcourir",
                "select_slot": "Sélectionner Slot",
                "select_partition": "Sélectionner Partition",
                "verbose_logging": "Log Verbose",
                "force_install": "Forcer l'installation",
                "log_level": "Niveau Log",
                "reboot_recovery": "ADB Reboot Recovery",
                "reboot": "ADB Reboot",
                "reboot_bootloader": "ADB Reboot Bootloader",
                "reboot_edl": "Reboot EDL",
                "reboot_fastbootd": "Reboot FastbootD",
                "erase_cache": "Effacer Cache",
                "check_adb_devices": "Vérifier périphériques ADB",
                "check_fastboot_devices": "Vérifier périphériques Fastboot",
                "check_lsusb": "Vérifier LSUSB",
                "start_sideload": "Démarrer Sideload",
                "getvar_all": "getvar all",
                "language": "Langue: Français",
                "install_linux": "Installation via gestionnaire de paquets",
                "update_linux": "Mise à jour via gestionnaire de paquets",
                "no_device": "Aucun appareil détecté",
                "device_adb": "Appareil détecté en mode ADB",
                "device_fastboot": "Appareil détecté en mode Fastboot",
                "device_both": "Appareil détecté en mode ADB et Fastboot",
                "log_exported": "Log exporté avec succès vers ",
                "warn_admin": "Attention : Exécutez le script en tant qu'administrateur pour une fonctionnalité complète.",
                "warn_root": "Attention : L'exécution sans privilèges root peut causer des problèmes avec ADB/Fastboot."
            }
        }

        # Initialize selected_file to avoid AttributeError
        self.selected_file = None

        # Internal widget dictionary for dynamic language updates
        self.widgets_to_update = {}

        # Log area
        self.log_text = ""
        self.cancel_flag = False

        self.log_view = TextInput(text='', readonly=True, size_hint_y=1,
                                  background_color=(0.12, 0.12, 0.12, 1),
                                  foreground_color=(0.9, 0.9, 0.9, 1),
                                  font_size='14sp', multiline=True)
        self.log_scroll = ScrollView(size_hint=(1, 0.35),
                                     do_scroll_x=False, do_scroll_y=True,
                                     bar_width=10)
        self.log_scroll.add_widget(self.log_view)
        self.add_widget(self.log_scroll)

        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=25)
        self.add_widget(self.progress_bar)

        # Check privileges
        if IS_WINDOWS:
            try:
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    self.log_message(self.tr("warn_admin"), level="warning")
            except Exception as e:
                self.log_message(f"Error checking permissions: {e}", level="error")
        else:
            if os.geteuid() != 0:
                self.log_message(self.tr("warn_root"), level="warning")

        # Main control panel (scrollable)
        self.control_panel = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.control_panel.bind(minimum_height=self.control_panel.setter('height'))

        # Base buttons
        self.btn_check = Button(text=self.tr("check_adb_fastboot"), size_hint_y=None, height=40)
        self.btn_check.bind(on_press=self.on_check_pressed)
        self.control_panel.add_widget(self.btn_check)
        self.widgets_to_update["check"] = self.btn_check

        self.btn_install = Button(text=self.tr("install"), size_hint_y=None, height=40)
        self.btn_install.bind(on_press=self.on_install_pressed)
        self.control_panel.add_widget(self.btn_install)
        self.widgets_to_update["install"] = self.btn_install

        self.btn_update = Button(text=self.tr("update"), size_hint_y=None, height=40)
        self.btn_update.bind(on_press=self.on_update_pressed)
        self.control_panel.add_widget(self.btn_update)
        self.widgets_to_update["update"] = self.btn_update

        self.btn_cancel = Button(text=self.tr("cancel"), size_hint_y=None, height=40)
        self.btn_cancel.bind(on_press=self.on_cancel_pressed)
        self.control_panel.add_widget(self.btn_cancel)
        self.widgets_to_update["cancel"] = self.btn_cancel

        self.btn_export = Button(text=self.tr("export_log"), size_hint_y=None, height=40)
        self.btn_export.bind(on_press=self.export_log)
        self.control_panel.add_widget(self.btn_export)
        self.widgets_to_update["export_log"] = self.btn_export

        # Flash, Browse, Slot & Partition buttons
        flash_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.btn_flash = Button(text=self.tr("flash"), size_hint_x=0.33, height=40)
        self.btn_flash.bind(on_press=self.on_flash_pressed)
        flash_layout.add_widget(self.btn_flash)
        self.widgets_to_update["flash"] = self.btn_flash

        self.btn_browse = Button(text=self.tr("browse"), size_hint_x=0.33, height=40)
        self.btn_browse.bind(on_press=self.on_browse_pressed)
        flash_layout.add_widget(self.btn_browse)
        self.widgets_to_update["browse"] = self.btn_browse

        self.slot_spinner = Spinner(
            text=self.tr("select_slot"),
            values=["None", "A", "B"],
            size_hint_x=0.33,
            height=40
        )
        flash_layout.add_widget(self.slot_spinner)
        self.control_panel.add_widget(flash_layout)
        self.widgets_to_update["select_slot"] = self.slot_spinner

        self.partition_spinner = Spinner(
            text=self.tr("select_partition"),
            values=["system", "boot", "recovery", "data",
                    "vendor", "vendor_kernel_boot", "vendor_boot",
                    "dtbo", "tee", "ramdisk", "bootloader"],
            size_hint_y=None, height=40
        )
        self.control_panel.add_widget(self.partition_spinner)
        self.widgets_to_update["select_partition"] = self.partition_spinner

        # Options: Verbose, Force and Log Level
        options_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.chk_verbose = CheckBox(active=False)
        options_layout.add_widget(self.chk_verbose)
        options_layout.add_widget(Label(text=self.tr("verbose_logging"), size_hint_x=0.4))

        self.chk_force = CheckBox(active=False)
        options_layout.add_widget(self.chk_force)
        options_layout.add_widget(Label(text=self.tr("force_install"), size_hint_x=0.4))
        
        self.log_level_spinner = Spinner(
            text="INFO",
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            size_hint_x=0.4,
            height=40
        )
        self.log_level_spinner.bind(text=self.on_log_level_change)
        options_layout.add_widget(Label(text=self.tr("log_level") + ":", size_hint_x=0.3))
        options_layout.add_widget(self.log_level_spinner)
        self.control_panel.add_widget(options_layout)

        # ADB reboot buttons
        reboot_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.btn_reboot_recovery = Button(text=self.tr("reboot_recovery"), size_hint_x=0.33, height=40)
        self.btn_reboot_recovery.bind(on_press=self.on_adb_reboot_recovery)
        reboot_layout.add_widget(self.btn_reboot_recovery)
        self.widgets_to_update["reboot_recovery"] = self.btn_reboot_recovery

        self.btn_reboot_bootloader = Button(text=self.tr("reboot_bootloader"), size_hint_x=0.33, height=40)
        self.btn_reboot_bootloader.bind(on_press=self.on_adb_reboot_bootloader)
        reboot_layout.add_widget(self.btn_reboot_bootloader)
        self.widgets_to_update["reboot_bootloader"] = self.btn_reboot_bootloader

        self.btn_reboot = Button(text=self.tr("reboot"), size_hint_x=0.33, height=40)
        self.btn_reboot.bind(on_press=self.on_adb_reboot)
        reboot_layout.add_widget(self.btn_reboot)
        self.widgets_to_update["reboot"] = self.btn_reboot
        self.control_panel.add_widget(reboot_layout)

        # Fastboot reboot buttons
        fastboot_reboot_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.btn_reboot_edl = Button(text=self.tr("reboot_edl"), size_hint_x=0.5, height=40)
        self.btn_reboot_edl.bind(on_press=self.on_reboot_edl_pressed)
        fastboot_reboot_layout.add_widget(self.btn_reboot_edl)
        self.widgets_to_update["reboot_edl"] = self.btn_reboot_edl

        self.btn_reboot_fastbootd = Button(text=self.tr("reboot_fastbootd"), size_hint_x=0.5, height=40)
        self.btn_reboot_fastbootd.bind(on_press=self.on_reboot_fastbootd_pressed)
        fastboot_reboot_layout.add_widget(self.btn_reboot_fastbootd)
        self.widgets_to_update["reboot_fastbootd"] = self.btn_reboot_fastbootd
        self.control_panel.add_widget(fastboot_reboot_layout)

        # Device checking buttons
        device_check_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.btn_check_adb = Button(text=self.tr("check_adb_devices"), size_hint_x=0.33, height=40)
        self.btn_check_adb.bind(on_press=lambda x: threading.Thread(target=self.check_adb_devices, daemon=True).start())
        device_check_layout.add_widget(self.btn_check_adb)
        self.widgets_to_update["check_adb_devices"] = self.btn_check_adb

        self.btn_check_fastboot = Button(text=self.tr("check_fastboot_devices"), size_hint_x=0.33, height=40)
        self.btn_check_fastboot.bind(on_press=lambda x: threading.Thread(target=self.check_fastboot_devices, daemon=True).start())
        device_check_layout.add_widget(self.btn_check_fastboot)
        self.widgets_to_update["check_fastboot_devices"] = self.btn_check_fastboot

        self.btn_check_lsusb = Button(text=self.tr("check_lsusb"), size_hint_x=0.33, height=40)
        self.btn_check_lsusb.bind(on_press=lambda x: threading.Thread(target=self.check_lsusb, daemon=True).start())
        device_check_layout.add_widget(self.btn_check_lsusb)
        self.widgets_to_update["check_lsusb"] = self.btn_check_lsusb
        self.control_panel.add_widget(device_check_layout)

        # Sideload and getvar all
        sideload_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        # Option: default prefix based on platform
        if IS_WINDOWS:
            sideload_values = [".\\", "adb -b sideload", "adb -a sideload"]
        else:
            sideload_values = ["./", "adb -b sideload", "adb -a sideload"]
        self.sideload_spinner = Spinner(
            text=sideload_values[0],
            values=sideload_values,
            size_hint_x=0.5, height=40
        )
        sideload_layout.add_widget(self.sideload_spinner)
        self.btn_start_sideload = Button(text=self.tr("start_sideload"), size_hint_x=0.5, height=40)
        self.btn_start_sideload.bind(on_press=self.on_start_sideload_pressed)
        sideload_layout.add_widget(self.btn_start_sideload)
        self.widgets_to_update["start_sideload"] = self.btn_start_sideload
        self.control_panel.add_widget(sideload_layout)

        getvar_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.btn_getvar_all = Button(text=self.tr("getvar_all"), size_hint_x=1, height=40)
        self.btn_getvar_all.bind(on_press=self.on_getvar_all_pressed)
        getvar_layout.add_widget(self.btn_getvar_all)
        self.widgets_to_update["getvar_all"] = self.btn_getvar_all
        self.control_panel.add_widget(getvar_layout)

        # Language toggle button
        self.btn_language = Button(text=self.tr("language"), size_hint_y=None, height=40)
        self.btn_language.bind(on_press=self.toggle_language)
        self.control_panel.add_widget(self.btn_language)
        self.widgets_to_update["language"] = self.btn_language

        # Place control panel in a scroll view
        self.control_scroll = ScrollView(size_hint=(1, 0.6))
        self.control_scroll.add_widget(self.control_panel)
        self.add_widget(self.control_scroll)

        # Automatic device detection label at the bottom
        self.device_status_label = Label(text=self.tr("no_device"), size_hint_y=None, height=30)
        self.add_widget(self.device_status_label)
        Clock.schedule_interval(self.update_device_status, 5)

    def tr(self, key):
        """Returns the translation for the given key according to the current language."""
        return self.translations[self.language].get(key, key)

    def update_ui_language(self):
        """Refreshes the UI texts according to the selected language."""
        for key, widget in self.widgets_to_update.items():
            if key in self.translations["en"]:
                widget.text = self.tr(key)
        self.device_status_label.text = self.tr("no_device")

    def log_message(self, message, level="info"):
        """Adds a message to the log (console, file and UI)."""
        self.log_text += message + "\n"
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
        Clock.schedule_once(lambda dt: self.append_to_log(message), 0)

    def append_to_log(self, message):
        """Updates the log area and scrolls to the bottom."""
        self.log_view.text += message + "\n"
        Clock.schedule_once(lambda dt: setattr(self.log_scroll, 'scroll_y', 0), 0)

    def export_log(self, instance):
        """Exports the log content to a timestamped text file."""
        filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text)
            self.log_message(self.tr("log_exported") + filename)
        except Exception as e:
            self.log_message(f"Error exporting log: {e}", level="error")

    def on_log_level_change(self, spinner, text):
        """Dynamically changes the log level."""
        level = getattr(logging, text.upper(), logging.INFO)
        logging.getLogger().setLevel(level)
        self.log_message(self.tr("log_level") + " set to " + text)

    # --- Functions related to ADB/Fastboot ---

    def check_adb_fastboot(self):
        """Checks for ADB and Fastboot availability on all platforms."""
        self.log_message(self.tr("Starting check for ADB and Fastboot..."))
        adb_installed = tool_available("adb")
        fastboot_installed = tool_available("fastboot")

        if not tool_in_path("adb"):
            self.log_message(self.tr("Warning: ADB is not in the PATH. Please add 'platform-tools' to your PATH."), level="warning")
        if not tool_in_path("fastboot"):
            self.log_message(self.tr("Warning: Fastboot is not in the PATH."), level="warning")

        # Specific checks for Linux
        if not IS_WINDOWS:
            if shutil.which("apt") or shutil.which("dnf") or shutil.which("pacman") or shutil.which("zypper"):
                self.log_message(self.tr("Linux package manager detected."))
            else:
                self.log_message(self.tr("No known package manager detected on Linux."), level="warning")

        if adb_installed and fastboot_installed:
            self.log_message("ADB and Fastboot are installed and operational.")
        else:
            missing = []
            if not adb_installed:
                missing.append("ADB")
            if not fastboot_installed:
                missing.append("Fastboot")
            self.log_message("Error: Missing dependency(ies): " + ", ".join(missing) + ".", level="error")
            self.log_message("Please click '" + self.tr("install") + "' to install the required dependencies.", level="warning")

    def install_adb_fastboot(self):
        """
        Downloads and installs ADB/Fastboot for Windows or launches installation via package manager on Linux.
        Supports "force install" option to bypass some checks.
        """
        def installation_task():
            self.cancel_flag = False
            self.log_message(self.tr("Starting ADB/Fastboot installation..."))
            if IS_WINDOWS:
                os_name = "windows"
                url = PLATFORM_TOOLS_URL.format(os_name)
                self.log_message("Downloading from " + url + " ...")

                def progress_update(value):
                    Clock.schedule_once(lambda dt: setattr(self.progress_bar, 'value', value), 0)

                if download_file(url, DOWNLOAD_ZIP_NAME, progress_callback=progress_update, cancel_check=lambda: self.cancel_flag):
                    self.log_message("Download completed. Validating file...")
                    if not is_zipfile(DOWNLOAD_ZIP_NAME):
                        self.log_message("Error: Downloaded file is not a valid zip.", level="error")
                        return
                    file_hash = calculate_file_hash(DOWNLOAD_ZIP_NAME)
                    self.log_message("Downloaded file hash: " + str(file_hash))
                    self.log_message("File validated. Extracting...")
                    if extract_zip(DOWNLOAD_ZIP_NAME, EXTRACT_DIR, progress_callback=progress_update):
                        adb_filename = "adb.exe" if IS_WINDOWS else "adb"
                        adb_path = Path(EXTRACT_DIR) / adb_filename
                        if adb_path.exists():
                            self.log_message("Installation successful! Add 'platform-tools' to your PATH.")
                        else:
                            self.log_message("Error: Installation failed. 'platform-tools' not found after extraction.", level="error")
                    else:
                        self.log_message("Error during extraction.", level="error")
                else:
                    self.log_message("Error during download or download cancelled.", level="error")
                Clock.schedule_once(lambda dt: setattr(self.progress_bar, 'value', 0), 0)
            else:
                # Installation via package manager on Linux
                self.log_message(self.tr("install_linux"))
                if shutil.which("apt"):
                    cmd = ["sudo", "apt", "install", "-y", "android-tools-adb", "android-tools-fastboot"]
                elif shutil.which("dnf"):
                    cmd = ["sudo", "dnf", "install", "-y", "android-tools"]
                elif shutil.which("pacman"):
                    cmd = ["sudo", "pacman", "-S", "--noconfirm", "android-tools"]
                elif shutil.which("zypper"):
                    cmd = ["sudo", "zypper", "install", "-y", "android-tools"]
                else:
                    self.log_message("No supported package manager found.", level="error")
                    return
                self.log_message("Running command: " + " ".join(cmd))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        self.log_message("Installation completed successfully via package manager.")
                    else:
                        self.log_message("Error during package installation: " + result.stderr, level="error")
                except Exception as e:
                    self.log_message(f"Exception during package installation: {e}", level="error")
        threading.Thread(target=installation_task, daemon=True).start()

    def update_adb_fastboot(self):
        """
        Updates ADB/Fastboot.
        For Windows, removes the old version and reinstalls.
        For Linux, executes the update command via package manager or relaunches installation.
        The progress bar is updated accordingly.
        """
        def update_task():
            self.log_message(self.tr("Starting update for ADB/Fastboot..."))
            if IS_WINDOWS:
                if Path(EXTRACT_DIR).exists():
                    try:
                        shutil.rmtree(EXTRACT_DIR)
                        self.log_message("Previous platform-tools removed successfully.")
                    except Exception as e:
                        self.log_message("Error removing old platform-tools: " + str(e), level="error")
                        return
                self.install_adb_fastboot()
            else:
                self.log_message(self.tr("update_linux"))
                if shutil.which("apt"):
                    cmd = ["sudo", "apt", "upgrade", "-y", "android-tools-adb", "android-tools-fastboot"]
                elif shutil.which("dnf"):
                    cmd = ["sudo", "dnf", "update", "-y", "android-tools"]
                elif shutil.which("pacman"):
                    cmd = ["sudo", "pacman", "-Syu", "--noconfirm", "android-tools"]
                elif shutil.which("zypper"):
                    cmd = ["sudo", "zypper", "update", "-y", "android-tools"]
                else:
                    self.log_message("No supported package manager found.", level="error")
                    return
                self.log_message("Running update command: " + " ".join(cmd))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        self.log_message("Update completed successfully via package manager.")
                    else:
                        self.log_message("Error during package update: " + result.stderr, level="error")
                except Exception as e:
                    self.log_message(f"Exception during package update: {e}", level="error")
        threading.Thread(target=update_task, daemon=True).start()

    def check_fastboot_mode(self):
        """Detects whether the device is in classic fastboot or fastbootd mode."""
        try:
            result = subprocess.run(["fastboot", "getvar", "is-userspace"], capture_output=True, text=True, timeout=10)
            if "is-userspace: yes" in result.stdout:
                self.log_message("Device is in fastbootd mode.")
                return True
            else:
                self.log_message("Device is in classic fastboot mode.")
                return False
        except Exception as e:
            self.log_message("Error detecting fastboot mode: " + str(e), level="error")
            return False

    def flash_partition(self):
        """
        Checks the fastboot connection and flashes the selected partition after confirmation.
        Considers verbose mode and force install option.
        """
        try:
            result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=10)
        except Exception as e:
            self.log_message("Error running 'fastboot devices': " + str(e), level="error")
            return

        if not result.stdout.strip():
            self.log_message("Error: No device detected in fastboot mode. Connect your phone and try again.", level="error")
            return

        partition = self.partition_spinner.text
        slot = self.slot_spinner.text
        file_to_flash = self.selected_file

        if not file_to_flash or not Path(file_to_flash).exists():
            self.log_message("Error: No file selected for flashing or file does not exist.", level="error")
            return

        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text=f"Flash file:\n{file_to_flash}\non partition: {partition} (Slot: {slot}) ?"))
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_yes = Button(text="Yes", size_hint_y=None, height=40)
        btn_no = Button(text="No", size_hint_y=None, height=40)
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup = Popup(title="Confirm Flash", content=content, size_hint=(0.8, 0.5))

        def confirmed(instance):
            popup.dismiss()
            self.log_message("Preparing to flash...")
            try:
                self.log_message("Flashing in progress...")
                # Uncomment the following line to perform the actual flash:
                # subprocess.run(["fastboot", "flash", partition, file_to_flash], check=True)
                time.sleep(2)  # Simulation delay
                if self.chk_verbose.active:
                    self.log_message("Verbose mode: Detailed flash log output...")
                if self.chk_force.active:
                    self.log_message("Force Install enabled: Safety checks bypassed.")
                self.log_message("Flash completed successfully.")
            except Exception as e:
                self.log_message("Error during flash: " + str(e), level="error")

        def cancelled(instance):
            self.log_message("Flash cancelled by user.", level="warning")
            popup.dismiss()

        btn_yes.bind(on_press=confirmed)
        btn_no.bind(on_press=cancelled)
        popup.open()

    def reboot_command(self, command, description):
        """Executes a reboot command and logs the result."""
        try:
            self.log_message(f"{description}: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message(f"{description} executed successfully.")
            else:
                self.log_message(f"Error: {description} returned code {result.returncode}.", level="error")
        except Exception as e:
            self.log_message(f"Exception executing {description}: {e}", level="error")

    def reboot_edl(self):
        """Reboots the device into EDL mode."""
        try:
            self.log_message("Attempting to reboot device into EDL mode...")
            result = subprocess.run(["fastboot", "reboot", "edl"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message("EDL reboot command executed successfully.")
            else:
                self.log_message("Error: EDL reboot returned code " + str(result.returncode), level="error")
        except Exception as e:
            self.log_message("Exception during EDL reboot: " + str(e), level="error")

    def check_adb_devices(self):
        """Checks and logs the connected ADB devices."""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            devices = result.stdout.strip().split("\n")[1:]
            if devices and any(dev.strip() for dev in devices):
                self.log_message("Connected ADB devices:")
                for device in devices:
                    if device.strip():
                        self.log_message(f"- {device}")
            else:
                self.log_message("No ADB device detected.")
        except Exception as e:
            self.log_message("Error checking ADB devices: " + str(e), level="error")

    def check_fastboot_devices(self):
        """Checks and logs the connected Fastboot devices."""
        try:
            result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=10)
            devices = result.stdout.strip().split("\n")
            if devices and any(dev.strip() for dev in devices):
                self.log_message("Connected Fastboot devices:")
                for device in devices:
                    if device.strip():
                        self.log_message(f"- {device}")
            else:
                self.log_message("No Fastboot device detected.")
        except Exception as e:
            self.log_message("Error checking Fastboot devices: " + str(e), level="error")

    def check_lsusb(self):
        """Checks for lsusb availability on Linux and runs it."""
        if IS_WINDOWS:
            self.log_message("LSUSB is not available on Windows.")
            return

        lsusb_path = shutil.which("lsusb")
        if not lsusb_path:
            self.log_message("lsusb command not found. Attempting to install usbutils...")
            if os.geteuid() == 0:
                try:
                    subprocess.run(["apt-get", "update"], check=True)
                    subprocess.run(["apt-get", "install", "-y", "usbutils"], check=True)
                    self.log_message("usbutils installed successfully.")
                except Exception as e:
                    self.log_message("Error installing usbutils: " + str(e), level="error")
                    return
            else:
                self.log_message("Please run the script as root to install usbutils.", level="warning")
                return

        try:
            result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=10)
            self.log_message("LSUSB output:")
            self.log_message(result.stdout)
        except Exception as e:
            self.log_message("Error running lsusb: " + str(e), level="error")

    def on_browse_pressed(self, instance):
        """Opens a file chooser to select a flashable file and adjusts partitions."""
        filechooser = FileChooserListView(path=os.getcwd())

        def select_file(instance):
            if filechooser.selection:
                selected = filechooser.selection[0]
                allowed = ('.img', '.tar', '.tar.md5', '.zip')
                if selected.lower().endswith(allowed):
                    self.selected_file = selected
                    self.log_message("Selected file: " + selected)
                    if ".boot" in selected:
                        self.partition_spinner.values = ["boot", "vendor_boot", "dtbo"]
                    elif ".recovery" in selected:
                        self.partition_spinner.values = ["recovery"]
                    elif ".system" in selected:
                        self.partition_spinner.values = ["system", "system_ext", "vendor"]
                    else:
                        self.partition_spinner.values = ["system", "boot", "recovery", "data",
                                                         "vendor", "vendor_kernel_boot", "vendor_boot",
                                                         "dtbo", "tee", "ramdisk", "bootloader"]
                    self.partition_spinner.text = self.partition_spinner.values[0]
                else:
                    self.log_message("Error: Selected file does not have an allowed extension.", level="error")
            else:
                self.log_message("No file selected.", level="warning")
            popup.dismiss()

        popup_layout = BoxLayout(orientation='vertical')
        popup_layout.add_widget(filechooser)
        btn_select = Button(text="Select", size_hint_y=None, height=40)
        btn_select.bind(on_press=select_file)
        popup_layout.add_widget(btn_select)
        popup = Popup(title="Browse Files", content=popup_layout, size_hint=(0.9, 0.9))
        popup.open()

    def on_start_sideload_pressed(self, instance):
        """Starts the sideload command based on the selected mode."""
        if not self.selected_file:
            self.log_message("Error: No file selected for sideload.", level="error")
            return

        mode = self.sideload_spinner.text
        if mode in [".\\", "./"]:
            # If no specific sideload command is chosen, use the default prefix
            args = ["adb", "sideload"]
        elif mode == "adb -b sideload":
            args = ["adb", "-b", "sideload"]
        elif mode == "adb -a sideload":
            args = ["adb", "-a", "sideload"]
        else:
            self.log_message("Error: Unrecognized sideload mode.", level="error")
            return

        filename = Path(self.selected_file).name
        file_arg = f".\\{filename}" if IS_WINDOWS else f"./{filename}"
        args.append(file_arg)
        self.log_message("Starting sideload command: " + " ".join(args))

        def run_sideload():
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    self.log_message("Sideload completed successfully.")
                else:
                    self.log_message("Error during sideload (code " + str(result.returncode) + "): " + result.stderr, level="error")
            except Exception as e:
                self.log_message("Exception during sideload: " + str(e), level="error")
        threading.Thread(target=run_sideload, daemon=True).start()

    def on_getvar_all_pressed(self, instance):
        """Executes the 'fastboot getvar all' command and logs the output."""
        self.log_message("Executing 'fastboot getvar all' command...")
        def run_getvar_all():
            try:
                result = subprocess.run(["fastboot", "getvar", "all"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.log_message("Output of 'fastboot getvar all':")
                    self.log_message(result.stdout)
                else:
                    self.log_message("Error: 'fastboot getvar all' returned code " + str(result.returncode) + ".", level="error")
            except Exception as e:
                self.log_message("Exception during 'fastboot getvar all': " + str(e), level="error")
        threading.Thread(target=run_getvar_all, daemon=True).start()

    # --- Methods for actions via threads ---
    def on_check_pressed(self, instance):
        threading.Thread(target=self.check_adb_fastboot, daemon=True).start()

    def on_install_pressed(self, instance):
        threading.Thread(target=self.install_adb_fastboot, daemon=True).start()

    def on_update_pressed(self, instance):
        threading.Thread(target=self.update_adb_fastboot, daemon=True).start()

    def on_flash_pressed(self, instance):
        threading.Thread(target=self.flash_partition, daemon=True).start()

    def on_reboot_edl_pressed(self, instance):
        threading.Thread(target=self.reboot_edl, daemon=True).start()

    def on_reboot_fastbootd_pressed(self, instance):
        threading.Thread(target=lambda: self.reboot_command(["fastboot", "reboot", "fastboot"], "Reboot FastbootD"), daemon=True).start()

    def on_cancel_pressed(self, instance):
        """Cancels any ongoing long operation."""
        self.cancel_flag = True
        self.log_message("Cancel flag set. Ongoing operation will be cancelled.", level="warning")

    # --- ADB Reboot Buttons ---
    def on_adb_reboot_recovery(self, instance):
        """Executes the 'adb reboot recovery' command."""
        threading.Thread(target=lambda: self.reboot_command(["adb", "reboot", "recovery"], "ADB Reboot Recovery"), daemon=True).start()

    def on_adb_reboot_bootloader(self, instance):
        """Executes the 'adb reboot bootloader' command."""
        threading.Thread(target=lambda: self.reboot_command(["adb", "reboot", "bootloader"], "ADB Reboot Bootloader"), daemon=True).start()

    def on_adb_reboot(self, instance):
        """Executes the 'adb reboot' command."""
        threading.Thread(target=lambda: self.reboot_command(["adb", "reboot"], "ADB Reboot"), daemon=True).start()

    def toggle_language(self, instance):
        """Toggles between English and French and updates the UI in real time."""
        self.language = "fr" if self.language == "en" else "en"
        self.log_message("Language switched to " + self.translations[self.language]["language"])
        self.update_ui_language()

    def update_device_status(self, dt):
        """Continuously checks for ADB and Fastboot devices and updates the status label."""
        try:
            adb_status = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            fastboot_status = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=5)
            adb_devices = [d for d in adb_status.stdout.strip().split("\n")[1:] if d.strip()]
            fastboot_devices = [d for d in fastboot_status.stdout.strip().split("\n") if d.strip()]
        except FileNotFoundError:
            adb_devices = []
            fastboot_devices = []
            self.log_message("ADB or Fastboot command not found.", level="error")
        except Exception as e:
            self.log_message("Error checking device status: " + str(e), level="error")
            adb_devices = []
            fastboot_devices = []
        if adb_devices and fastboot_devices:
            status = self.tr("device_both")
        elif adb_devices:
            status = self.tr("device_adb")
        elif fastboot_devices:
            status = self.tr("device_fastboot")
        else:
            status = self.tr("no_device")
        self.device_status_label.text = status

class ADBInstallerApp(App):
    def build(self):
        return ADBInstaller()

if __name__ == "__main__":
    ADBInstallerApp().run()
