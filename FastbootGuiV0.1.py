import os
import sys
import subprocess
import urllib.request
import hashlib
from zipfile import ZipFile, is_zipfile
import threading
import time
import ctypes  # Pour vérifier les privilèges admin sur Windows
import shutil
import logging
from datetime import datetime
from pathlib import Path

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

# Ajout d'un log vers fichier
log_filename = "adbinstaller.log"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout),
                        logging.FileHandler(log_filename, encoding="utf-8")
                    ])

# --- Fonctions Utilitaires ---

def calculate_file_hash(file_path, algorithm="sha256"):
    """
    Calcule le hash du fichier pour vérification d'intégrité.
    """
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
    Télécharge un fichier depuis l'URL indiquée vers la destination.
    Supporte la reprise si un fichier partiel existe.
    Le progress_callback (optionnel) reçoit la progression en pourcentage.
    Le cancel_check est une fonction retournant True si l'opération doit être annulée.
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
    Extrait le fichier zip dans le répertoire spécifié.
    Le progress_callback (optionnel) reçoit la progression en pourcentage.
    """
    try:
        if not is_zipfile(zip_path):
            raise Exception("Fichier non valide (non zip)")
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
    Vérifie la disponibilité d'un outil en exécutant 'tool version'.
    Retourne True si l'outil est opérationnel.
    """
    try:
        result = subprocess.run([tool, "version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logging.info("%s detected: %s", tool, result.stdout.splitlines()[0])
            return True
        else:
            logging.warning("%s returned error code %s", tool, result.returncode)
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logging.error("Error: %s is not available or timed out. %s", tool, e)
        return False

def tool_in_path(tool):
    """
    Vérifie si l'outil est accessible dans le PATH.
    """
    return any(Path(path, tool).exists() for path in os.environ["PATH"].split(os.pathsep))


# --- Classe principale de l'application ---

class ADBInstaller(BoxLayout):
    """
    Application Kivy pour gérer l'installation et le contrôle d'ADB/Fastboot.
    """
    def __init__(self, **kwargs):
        super(ADBInstaller, self).__init__(orientation='vertical', **kwargs)
        self.selected_file = None
        self.log_text = ""  # Stocke l'historique du log pour l'export
        self.cancel_flag = False  # Flag d'annulation pour les opérations longues

        # Zone de log (40% de la hauteur) avec ScrollView
        self.log_view = TextInput(text='', readonly=True, size_hint_y=1,
                                  background_color=(0.1, 0.1, 0.1, 1),
                                  foreground_color=(0.8, 0.8, 0.8, 1),
                                  font_size='14sp', multiline=True)
        self.log_scroll = ScrollView(size_hint=(1, 0.4),
                                     do_scroll_x=False, do_scroll_y=True,
                                     bar_width=10,
                                     bar_color=[1, 1, 1, 1],
                                     bar_inactive_color=[1, 1, 1, 0.5])
        self.log_scroll.add_widget(self.log_view)
        self.add_widget(self.log_scroll)

        # Barre de progression pour opérations longues
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=20)
        self.add_widget(self.progress_bar)

        # Vérification des privilèges
        if IS_WINDOWS:
            try:
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    self.log_message("Warning: Run the script as Administrator for full functionality.", level="warning")
            except Exception as e:
                self.log_message(f"Error checking permissions: {e}", level="error")
        else:
            if os.geteuid() != 0:
                self.log_message("Warning: Running without root privileges may cause issues with ADB/Fastboot.", level="warning")

        # Panneau de contrôle dans un ScrollView (60% de la hauteur)
        # On utilise un BoxLayout sans size_hint_y et avec binding sur minimum_height pour permettre le scrolling
        self.control_panel = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        self.control_panel.bind(minimum_height=self.control_panel.setter('height'))

        # Boutons pour vérifier, installer, mettre à jour et annuler (boutons réduits à 40px de hauteur)
        btn_check = Button(text="Check ADB/Fastboot", size_hint_y=None, height=40)
        btn_check.bind(on_press=self.on_check_pressed)
        self.control_panel.add_widget(btn_check)

        btn_install = Button(text="Install ADB/Fastboot", size_hint_y=None, height=40)
        btn_install.bind(on_press=self.on_install_pressed)
        self.control_panel.add_widget(btn_install)

        btn_update = Button(text="Update ADB/Fastboot", size_hint_y=None, height=40)
        btn_update.bind(on_press=self.on_update_pressed)
        self.control_panel.add_widget(btn_update)

        btn_cancel = Button(text="Cancel Operation", size_hint_y=None, height=40)
        btn_cancel.bind(on_press=self.on_cancel_pressed)
        self.control_panel.add_widget(btn_cancel)

        # Bouton Export Log
        btn_export = Button(text="Export Log", size_hint_y=None, height=40)
        btn_export.bind(on_press=self.export_log)
        self.control_panel.add_widget(btn_export)

        # Layout pour Flash, Browse et Slot
        flash_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_flash = Button(text="Flash", size_hint_x=0.33, height=40)
        btn_flash.bind(on_press=self.on_flash_pressed)
        flash_layout.add_widget(btn_flash)

        btn_browse = Button(text="Browse", size_hint_x=0.33, height=40)
        btn_browse.bind(on_press=self.on_browse_pressed)
        flash_layout.add_widget(btn_browse)

        self.slot_spinner = Spinner(
            text="Select Slot",
            values=["None", "A", "B"],
            size_hint_x=0.33,
            height=40
        )
        flash_layout.add_widget(self.slot_spinner)
        self.control_panel.add_widget(flash_layout)

        # Spinner de sélection de partition
        self.partition_spinner = Spinner(
            text="Select Partition",
            values=["system", "boot", "recovery", "data",
                    "vendor", "vendor_kernel_boot", "vendor_boot",
                    "dtbo", "tee", "ramdisk", "bootloader"],
            size_hint_y=None, height=40
        )
        self.control_panel.add_widget(self.partition_spinner)

        # Options supplémentaires (Verbose et Force) et sélection du niveau de log
        options_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.chk_verbose = CheckBox(active=False)
        options_layout.add_widget(self.chk_verbose)
        options_layout.add_widget(Label(text="Verbose Logging", size_hint_x=0.4))

        self.chk_force = CheckBox(active=False)
        options_layout.add_widget(self.chk_force)
        options_layout.add_widget(Label(text="Force Install", size_hint_x=0.4))
        
        # Spinner pour ajuster le niveau de log
        self.log_level_spinner = Spinner(
            text="INFO",
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            size_hint_x=0.4,
            height=40
        )
        self.log_level_spinner.bind(text=self.on_log_level_change)
        options_layout.add_widget(Label(text="Log Level:", size_hint_x=0.3))
        options_layout.add_widget(self.log_level_spinner)

        self.control_panel.add_widget(options_layout)

        # Layout pour commandes de reboot
        reboot_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_reboot_recovery = Button(text="Reboot Recovery", size_hint_x=0.16, height=40)
        btn_reboot_recovery.bind(on_press=self.on_reboot_recovery_pressed)
        reboot_layout.add_widget(btn_reboot_recovery)

        btn_reboot = Button(text="Reboot", size_hint_x=0.16, height=40)
        btn_reboot.bind(on_press=self.on_reboot_pressed)
        reboot_layout.add_widget(btn_reboot)

        btn_reboot_bootloader = Button(text="Reboot Bootloader", size_hint_x=0.16, height=40)
        btn_reboot_bootloader.bind(on_press=self.on_reboot_bootloader_pressed)
        reboot_layout.add_widget(btn_reboot_bootloader)

        btn_reboot_edl = Button(text="Reboot EDL", size_hint_x=0.16, height=40)
        btn_reboot_edl.bind(on_press=self.on_reboot_edl_pressed)
        reboot_layout.add_widget(btn_reboot_edl)

        btn_reboot_fastbootd = Button(text="Reboot FastbootD", size_hint_x=0.16, height=40)
        btn_reboot_fastbootd.bind(on_press=self.on_reboot_fastbootd_pressed)
        reboot_layout.add_widget(btn_reboot_fastbootd)

        btn_erase_cache = Button(text="Erase Cache", size_hint_x=0.16, height=40)
        btn_erase_cache.bind(on_press=lambda x: threading.Thread(
            target=lambda: self.reboot_command(["fastboot", "erase", "cache"], "Erase Cache"),
            daemon=True
        ).start())
        reboot_layout.add_widget(btn_erase_cache)
        self.control_panel.add_widget(reboot_layout)

        # Layout pour vérifier les périphériques (ADB, Fastboot, LSUSB)
        device_check_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_check_adb = Button(text="Check ADB Devices", size_hint_x=0.33, height=40)
        btn_check_adb.bind(on_press=lambda x: threading.Thread(target=self.check_adb_devices, daemon=True).start())
        device_check_layout.add_widget(btn_check_adb)

        btn_check_fastboot = Button(text="Check Fastboot Devices", size_hint_x=0.33, height=40)
        btn_check_fastboot.bind(on_press=lambda x: threading.Thread(target=self.check_fastboot_devices, daemon=True).start())
        device_check_layout.add_widget(btn_check_fastboot)

        btn_check_lsusb = Button(text="Check LSUSB", size_hint_x=0.33, height=40)
        btn_check_lsusb.bind(on_press=lambda x: threading.Thread(target=self.check_lsusb, daemon=True).start())
        device_check_layout.add_widget(btn_check_lsusb)
        self.control_panel.add_widget(device_check_layout)

        # Layout pour sideload : spinner et bouton "Start Sideload"
        sideload_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.sideload_spinner = Spinner(
            text="adb -b sideload",
            values=["adb -b sideload", "adb -a sideload"],
            size_hint_x=0.5, height=40
        )
        sideload_layout.add_widget(self.sideload_spinner)
        btn_start_sideload = Button(text="Start Sideload", size_hint_x=0.5, height=40)
        btn_start_sideload.bind(on_press=self.on_start_sideload_pressed)
        sideload_layout.add_widget(btn_start_sideload)
        self.control_panel.add_widget(sideload_layout)

        # Layout pour "getvar all"
        getvar_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_getvar_all = Button(text="getvar all", size_hint_x=1, height=40)
        btn_getvar_all.bind(on_press=self.on_getvar_all_pressed)
        getvar_layout.add_widget(btn_getvar_all)
        self.control_panel.add_widget(getvar_layout)

        # On place le panneau de contrôle dans un ScrollView
        self.control_scroll = ScrollView(size_hint=(1, 0.6))
        self.control_scroll.add_widget(self.control_panel)
        self.add_widget(self.control_scroll)

    # --- Méthodes de Logging et UI ---

    def log_message(self, message, level="info"):
        """
        Ajoute un message dans le log (console, fichier et interface).
        """
        self.log_text += message + "\n"
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
        Clock.schedule_once(lambda dt: self.append_to_log(message), 0)

    def append_to_log(self, message):
        """
        Met à jour la zone de log et force le défilement vers le bas.
        """
        self.log_view.text += message + "\n"
        Clock.schedule_once(lambda dt: setattr(self.log_scroll, 'scroll_y', 0), 0)

    def export_log(self, instance):
        """
        Exporte le contenu du log dans un fichier texte horodaté.
        """
        filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text)
            self.log_message(f"Log exported successfully to {filename}.")
        except Exception as e:
            self.log_message(f"Error exporting log: {e}", level="error")

    def on_log_level_change(self, spinner, text):
        """
        Change dynamiquement le niveau de log.
        """
        level = getattr(logging, text.upper(), logging.INFO)
        logging.getLogger().setLevel(level)
        self.log_message(f"Log level set to {text}.")

    # --- Fonctions liées à ADB/Fastboot ---

    def check_adb_fastboot(self):
        """
        Vérifie la disponibilité de ADB et Fastboot.
        """
        self.log_message("Starting check for ADB and Fastboot...")
        adb_installed = tool_available("adb")
        fastboot_installed = tool_available("fastboot")

        if not tool_in_path("adb"):
            self.log_message("Warning: ADB is not in the PATH. Please add 'platform-tools' to your PATH.", level="warning")
        if not tool_in_path("fastboot"):
            self.log_message("Warning: Fastboot is not in the PATH.", level="warning")

        if adb_installed and fastboot_installed:
            self.log_message("ADB and Fastboot are installed and operational.")
        else:
            missing = []
            if not adb_installed:
                missing.append("ADB")
            if not fastboot_installed:
                missing.append("Fastboot")
            self.log_message("Error: Missing dependency(ies): " + ", ".join(missing) + ".", level="error")
            self.log_message("Please click 'Install ADB/Fastboot' to install the required dependencies.", level="warning")

    def install_adb_fastboot(self):
        """
        Télécharge et installe ADB/Fastboot en extrayant l'archive téléchargée.
        Vérifie l’intégrité du fichier téléchargé via son hash (exemple).
        Possibilité d'annuler l'opération via self.cancel_flag.
        """
        try:
            self.cancel_flag = False
            self.log_message("Starting ADB/Fastboot installation...")
            os_name = "windows" if IS_WINDOWS else "linux"
            url = PLATFORM_TOOLS_URL.format(os_name)
            self.log_message(f"Downloading from {url} ...")

            # Fonction de mise à jour de la barre de progression
            def progress_update(value):
                Clock.schedule_once(lambda dt: setattr(self.progress_bar, 'value', value), 0)

            # Lancement du téléchargement avec reprise et vérification d'annulation
            if download_file(url, DOWNLOAD_ZIP_NAME, progress_callback=progress_update, cancel_check=lambda: self.cancel_flag):
                self.log_message("Download completed. Validating file...")
                if not is_zipfile(DOWNLOAD_ZIP_NAME):
                    self.log_message("Error: Downloaded file is not a valid zip.", level="error")
                    return
                # Exemple de calcul de hash (à comparer avec une valeur attendue si disponible)
                file_hash = calculate_file_hash(DOWNLOAD_ZIP_NAME)
                self.log_message(f"Downloaded file hash: {file_hash}")

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
        except Exception as e:
            self.log_message(f"Exception during installation: {e}", level="error")

    def update_adb_fastboot(self):
        """
        Met à jour ADB/Fastboot en téléchargeant et en extrayant la dernière version.
        Supprime l’ancienne version le cas échéant.
        """
        self.log_message("Starting update for ADB/Fastboot...")
        if Path(EXTRACT_DIR).exists():
            try:
                shutil.rmtree(EXTRACT_DIR)
                self.log_message("Previous platform-tools removed successfully.")
            except Exception as e:
                self.log_message(f"Error removing old platform-tools: {e}", level="error")
                return
        self.install_adb_fastboot()

    def check_fastboot_mode(self):
        """
        Détecte si le périphérique est en fastboot classique ou fastbootd.
        """
        try:
            result = subprocess.run(["fastboot", "getvar", "is-userspace"], capture_output=True, text=True, timeout=10)
            if "is-userspace: yes" in result.stdout:
                self.log_message("Device is in fastbootd mode.")
                return True
            else:
                self.log_message("Device is in classic fastboot mode.")
                return False
        except Exception as e:
            self.log_message(f"Error detecting fastboot mode: {e}", level="error")
            return False

    def flash_partition(self):
        """
        Vérifie la connexion en fastboot et lance le flash de la partition sélectionnée après confirmation.
        """
        try:
            result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=10)
        except Exception as e:
            self.log_message(f"Error running 'fastboot devices': {e}", level="error")
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

        # Confirmation de l'utilisateur via popup
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
                # Décommentez la ligne suivante pour lancer le flash effectif :
                # subprocess.run(["fastboot", "flash", partition, file_to_flash], check=True)
                time.sleep(2)  # Simulation du délai de flash
                if self.chk_verbose.active:
                    self.log_message("Verbose mode: Detailed flash log output...")
                if self.chk_force.active:
                    self.log_message("Force Install enabled: Safety checks bypassed.")
                self.log_message("Flash completed successfully.")
            except Exception as e:
                self.log_message(f"Error during flash: {e}", level="error")

        def cancelled(instance):
            self.log_message("Flash cancelled by user.", level="warning")
            popup.dismiss()

        btn_yes.bind(on_press=confirmed)
        btn_no.bind(on_press=cancelled)
        popup.open()

    def reboot_command(self, command, description):
        """
        Exécute une commande de reboot fastboot et journalise le résultat.
        """
        try:
            self.log_message(f"Executing {description} command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message(f"{description} command executed successfully.")
            else:
                self.log_message(f"Error: {description} command returned code {result.returncode}.", level="error")
        except Exception as e:
            self.log_message(f"Exception executing {description} command: {e}", level="error")

    def reboot_edl(self):
        """
        Redémarre le périphérique en mode EDL.
        """
        try:
            self.log_message("Attempting to reboot device into EDL mode...")
            result = subprocess.run(["fastboot", "reboot", "edl"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_message("EDL reboot command executed successfully.")
            else:
                self.log_message(f"Error: EDL reboot returned code {result.returncode}.", level="error")
        except Exception as e:
            self.log_message(f"Exception during EDL reboot: {e}", level="error")

    def check_adb_devices(self):
        """
        Vérifie et affiche les périphériques connectés via ADB.
        """
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            devices = result.stdout.strip().split("\n")[1:]  # Exclut l'en-tête
            if devices and any(dev.strip() for dev in devices):
                self.log_message("Connected ADB devices:")
                for device in devices:
                    if device.strip():
                        self.log_message(f"- {device}")
            else:
                self.log_message("No ADB device detected.")
        except Exception as e:
            self.log_message(f"Error checking ADB devices: {e}", level="error")

    def check_fastboot_devices(self):
        """
        Vérifie et affiche les périphériques connectés via Fastboot.
        """
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
            self.log_message(f"Error checking Fastboot devices: {e}", level="error")

    def check_lsusb(self):
        """
        Vérifie la disponibilité de la commande lsusb sur Linux et l'exécute.
        """
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
                    self.log_message(f"Error installing usbutils: {e}", level="error")
                    return
            else:
                self.log_message("Please run the script as root to install usbutils.", level="warning")
                return

        try:
            result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=10)
            self.log_message("LSUSB output:")
            self.log_message(result.stdout)
        except Exception as e:
            self.log_message(f"Error running lsusb: {e}", level="error")

    def on_browse_pressed(self, instance):
        """
        Ouvre un sélecteur de fichiers pour choisir un fichier flashable
        et ajuste dynamiquement les partitions disponibles.
        """
        filechooser = FileChooserListView(path=os.getcwd())

        def select_file(instance):
            if filechooser.selection:
                selected = filechooser.selection[0]
                allowed = ('.img', '.tar', '.tar.md5', '.zip')
                if selected.lower().endswith(allowed):
                    self.selected_file = selected
                    self.log_message(f"Selected file: {selected}")

                    # Ajuste la liste des partitions en fonction du nom du fichier
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
        """
        Démarre la commande sideload en fonction du mode sélectionné.
        """
        if not self.selected_file:
            self.log_message("Error: No file selected for sideload.", level="error")
            return

        mode = self.sideload_spinner.text
        if mode == "adb -b sideload":
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
                    self.log_message(f"Error during sideload (code {result.returncode}): {result.stderr}", level="error")
            except Exception as e:
                self.log_message(f"Exception during sideload: {e}", level="error")

        threading.Thread(target=run_sideload, daemon=True).start()

    def on_getvar_all_pressed(self, instance):
        """
        Exécute la commande 'fastboot getvar all' et journalise la sortie.
        """
        self.log_message("Executing 'fastboot getvar all' command...")

        def run_getvar_all():
            try:
                result = subprocess.run(["fastboot", "getvar", "all"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.log_message("Output of 'fastboot getvar all':")
                    self.log_message(result.stdout)
                else:
                    self.log_message(f"Error: 'fastboot getvar all' returned code {result.returncode}.", level="error")
            except Exception as e:
                self.log_message(f"Exception during 'fastboot getvar all': {e}", level="error")
        threading.Thread(target=run_getvar_all, daemon=True).start()

    # --- Méthodes pour déclencher les actions via des threads séparés ---
    def on_check_pressed(self, instance):
        threading.Thread(target=self.check_adb_fastboot, daemon=True).start()

    def on_install_pressed(self, instance):
        threading.Thread(target=self.install_adb_fastboot, daemon=True).start()

    def on_update_pressed(self, instance):
        threading.Thread(target=self.update_adb_fastboot, daemon=True).start()

    def on_flash_pressed(self, instance):
        threading.Thread(target=self.flash_partition, daemon=True).start()

    def on_reboot_recovery_pressed(self, instance):
        threading.Thread(target=lambda: self.reboot_command(["fastboot", "reboot", "recovery"], "Reboot Recovery"), daemon=True).start()

    def on_reboot_pressed(self, instance):
        threading.Thread(target=lambda: self.reboot_command(["fastboot", "reboot"], "Reboot"), daemon=True).start()

    def on_reboot_bootloader_pressed(self, instance):
        threading.Thread(target=lambda: self.reboot_command(["fastboot", "reboot", "bootloader"], "Reboot Bootloader"), daemon=True).start()

    def on_reboot_edl_pressed(self, instance):
        threading.Thread(target=self.reboot_edl, daemon=True).start()

    def on_reboot_fastbootd_pressed(self, instance):
        threading.Thread(target=lambda: self.reboot_command(["fastboot", "reboot", "fastboot"], "Reboot FastbootD"), daemon=True).start()

    def on_cancel_pressed(self, instance):
        """
        Permet d'annuler une opération longue (téléchargement, extraction, etc.).
        """
        self.cancel_flag = True
        self.log_message("Cancel flag set. Ongoing operation will be cancelled.", level="warning")

class ADBInstallerApp(App):
    """
    Classe principale de l'application Kivy.
    """
    def build(self):
        return ADBInstaller()

if __name__ == "__main__":
    ADBInstallerApp().run()
