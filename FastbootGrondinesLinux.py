import os
import json
import time
import platform
import subprocess
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window

# --- Dictionnaire de traductions ---
translations_dict = {
    "fr": {
        "menu_partition": "Partitions à flasher",
        "choose_slot": "Choisir un Slot",
        "no_slot": "Aucun Slot",
        "slot_a": "Slot A",
        "slot_b": "Slot B",
        "browse": "Parcourir",
        "flash": "Flasher",
        "reboot": "Reboot",
        "lock_bootloader": "Verrouiller Bootloader",
        "unlock_bootloader": "Déverrouiller Bootloader",
        "fastboot_getvar": "Fastboot GetVar All",
        "sideload": "Sideload",
        "flash_custom_os": "Flash Custom OS",
        "settings": "Paramètres",
        "help": "Aide",
        "udev_tab": "Règles udev",
        "flash_tab": "Flash",
        "sideload_tab": "Sideload",
        "custom_tab": "Flash Custom OS",
        "settings_tab": "Paramètres",
        "help_tab": "Aide",
        "diagnostic_tab": "Diagnostic",
        "diagnostic_history": "Historique des commandes exécutées",
        "device_fastboot_connected": "Appareil connecté en Fastboot",
        "device_adb_connected": "Appareil connecté en ADB",
        "no_device": "Aucun appareil connecté",
        "flash_started": "Flash démarré",
        "flash_completed": "Flash terminé",
        "command_error": "Erreur de commande",
        "colors_applied": "Couleurs appliquées",
        "clear_log": "Effacer le log",
        "save_log": "Sauvegarder le log",
        "command_reboot_sent": "Commande Reboot envoyée",
        "command_lock_sent": "Commande de verrouillage envoyée",
        "command_unlock_sent": "Commande de déverrouillage envoyée",
        "command_getvar_sent": "Commande fastboot getvar envoyée",
        "file_selected": "Fichier sélectionné",
        "command_flash_sent": "Commande Flash envoyée",
        "custom_os_instructions": (
            "Instructions pour flasher un firmware Custom :\n\n"
            "Ce module vous permet d'installer un firmware personnalisé sur votre appareil. Il est destiné à l'installation de ROMs custom, à la modification du bootloader et à d'autres réglages avancés du système.\n\n"
            "Utilisation :\n"
            " - Vérifiez que l'appareil est détecté en mode fastboot ou adb.\n"
            " - Sélectionnez les images à flasher (boot.img, dtbo.img, vendor_boot, etc.) selon les instructions affichées.\n"
            " - Suivez l'ordre recommandé : flashez d'abord les images disponibles, puis redémarrez en recovery pour utiliser 'Apply Update'.\n"
            " - Vous pouvez également utiliser adb sideload pour installer un package complet.\n\n"
            "Utilisations possibles :\n"
            " - Installation d'une ROM personnalisée\n"
            " - Mise à jour de composants spécifiques\n"
            " - Dépannage avancé et restauration de l'appareil\n"
            "Sauvegardez vos données avant toute opération de flash."
        ),
        "apply_translation": "Appliquer la traduction",
        "interface_color": "Couleur de l'interface",
        "log_color": "Couleur du log",
        "text_color": "Couleur du texte",
        "language": "Langue",
        "help_instructions": (
            "Instructions d'utilisation / Usage Instructions:\n\n"
            "1. Dans l'onglet Flash, sélectionnez la partition, le slot et le fichier à flasher, puis appuyez sur 'Flasher'.\n"
            "2. Dans l'onglet Sideload, choisissez un fichier .zip, sélectionnez le mode (adb -a ou adb -b) et lancez la commande.\n"
            "3. Utilisez les boutons de reboot, de verrouillage/déverrouillage, fastboot getvar, adb reboot bootloader/recovery, etc., pour gérer l'appareil.\n"
            "4. Les logs s'affichent en temps réel dans une zone scrollable, avec options pour les effacer ou les sauvegarder.\n"
            "5. L'onglet Diagnostic affiche l'historique des commandes exécutées pour le débogage.\n"
            "6. Tous les appels de commandes s'exécutent en multi-thread."
        ),
        "adb_reboot_bootloader": "adb reboot bootloader",
        "adb_reboot_recovery": "adb reboot recovery",
        "echo_flashing": "Flash en cours...",
        "echo_rebooting": "Redémarrage en cours...",
        "attempt_lock": "Tentative de verrouillage du bootloader...",
        "attempt_unlock": "Tentative de déverrouillage du bootloader...",
        "echo_sideload": "Exécution du sideload...",
        "cancel": "Annuler",
        "sideload_mode": "Mode sideload:",
        "confirmation": "Confirmation",
        "sudo_prompt": "Autoriser l'exécution des commandes sudo ?",
        "disable_theme": "Désactiver le thème",
        "execute_lsusb": "Exécuter lsusb",
        "install_dependencies": "Installer dépendances"
    },
    "en": {
        "menu_partition": "Partitions to Flash",
        "choose_slot": "Choose a Slot",
        "no_slot": "No Slot",
        "slot_a": "Slot A",
        "slot_b": "Slot B",
        "browse": "Browse",
        "flash": "Flash",
        "reboot": "Reboot",
        "lock_bootloader": "Lock Bootloader",
        "unlock_bootloader": "Unlock Bootloader",
        "fastboot_getvar": "Fastboot GetVar All",
        "sideload": "Sideload",
        "flash_custom_os": "Flash Custom OS",
        "settings": "Settings",
        "help": "Help",
        "udev_tab": "Udev Rules",
        "flash_tab": "Flash",
        "sideload_tab": "Sideload",
        "custom_tab": "Flash Custom OS",
        "settings_tab": "Settings",
        "help_tab": "Help",
        "diagnostic_tab": "Diagnostic",
        "diagnostic_history": "History of executed commands",
        "device_fastboot_connected": "Device Connected via Fastboot",
        "device_adb_connected": "Device connected via ADB",
        "no_device": "No device connected",
        "flash_started": "Flashing started",
        "flash_completed": "Flashing completed",
        "command_error": "Command error",
        "colors_applied": "Colors applied",
        "clear_log": "Clear Log",
        "save_log": "Save Log",
        "command_reboot_sent": "Reboot command sent",
        "command_lock_sent": "Lock Bootloader command sent",
        "command_unlock_sent": "Unlock Bootloader command sent",
        "command_getvar_sent": "Fastboot getvar command sent",
        "file_selected": "File selected",
        "command_flash_sent": "Flash command sent",
        "custom_os_instructions": (
            "Instructions for flashing a Custom Firmware:\n\n"
            "This module allows you to install a custom firmware on your device. It is designed for installing custom ROMs, modifying the bootloader, and other advanced system adjustments.\n\n"
            "Usage:\n"
            " - Ensure your device is detected in fastboot or adb mode.\n"
            " - Select the images to flash (boot.img, dtbo.img, vendor_boot, etc.) as indicated by the instructions displayed.\n"
            " - Follow the recommended order: first flash the available images, then reboot into recovery to use 'Apply Update'.\n"
            " - You can also use adb sideload to install a complete package.\n\n"
            "Possible uses include:\n"
            " - Installing a custom ROM\n"
            " - Updating specific system components\n"
            " - Advanced troubleshooting and device restoration\n"
            "Make sure to back up your data before any flash operation."
        ),
        "apply_translation": "Apply translation",
        "interface_color": "Interface Color",
        "log_color": "Log Color",
        "text_color": "Text Color",
        "language": "Language",
        "help_instructions": (
            "Usage Instructions:\n\n"
            "1. In the Flash tab, select the partition, slot, and file to flash, then press 'Flash'.\n"
            "2. In the Sideload tab, choose a .zip file, select the mode (adb -a or adb -b), and execute the command.\n"
            "3. Use the reboot, lock/unlock, fastboot getvar, adb reboot bootloader/recovery buttons, etc., to manage the device.\n"
            "4. Logs are displayed in real time in a scrollable area with options to clear or save them.\n"
            "5. The Diagnostic tab shows the history of executed commands for debugging.\n"
            "6. All commands run on multiple threads."
        ),
        "adb_reboot_bootloader": "adb reboot bootloader",
        "adb_reboot_recovery": "adb reboot recovery",
        "echo_flashing": "Flashing device...",
        "echo_rebooting": "Rebooting device...",
        "attempt_lock": "Attempting to lock bootloader...",
        "attempt_unlock": "Attempting to unlock bootloader...",
        "echo_sideload": "Executing sideload...",
        "cancel": "Cancel",
        "sideload_mode": "Sideload mode:",
        "confirmation": "Confirmation",
        "sudo_prompt": "Allow execution of sudo commands?",
        "disable_theme": "Disable theme",
        "execute_lsusb": "Execute lsusb",
        "install_dependencies": "Install dependencies"
    }
}
current_lang = "fr"

def t(key):
    return translations_dict[current_lang].get(key, key)

# --- Persistance des paramètres ---
SETTINGS_FILE = "user_settings.json"
default_settings = {
    "interface_color": [0.1, 0.1, 0.1, 1],  # Look cyberpunk sombre par défaut
    "log_color": [0.0, 0.0, 0.0, 1],
    "text_color": [0, 1, 1, 1],           # Texte en cyan néon
    "lang": "fr",
    "disable_theme": False
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_settings.copy()
    else:
        return default_settings.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception as e:
        print("Error saving settings:", e)

# --- Exécution des commandes en temps réel ---
def run_command_realtime(cmd, log_callback, diag_callback=None):
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=True, bufsize=1, universal_newlines=True)
        for line in iter(process.stdout.readline, ''):
            if line:
                Clock.schedule_once(lambda dt, l=line: log_callback(l.strip()))
                if diag_callback:
                    Clock.schedule_once(lambda dt, l=line: diag_callback("CMD: " + cmd + " >> " + l.strip()))
        process.stdout.close()
        process.wait()
        err = process.stderr.read()
        if err:
            Clock.schedule_once(lambda dt, err=err: log_callback(err.strip()))
            if diag_callback:
                Clock.schedule_once(lambda dt, err=err: diag_callback("CMD ERROR: " + cmd + " >> " + err.strip()))
    except Exception as e:
        Clock.schedule_once(lambda dt: log_callback(t("command_error") + ": " + str(e)))
        if diag_callback:
            Clock.schedule_once(lambda dt: diag_callback(t("command_error") + ": " + str(e)))

# --- Popup de sélection de fichier ---
class FileChooserPopup(Popup):
    popup_title = StringProperty(t("browse"))
    file_filter = StringProperty("*.zip")
    def __init__(self, callback, file_exts, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.file_filter = "*" + file_exts
    def select_file(self, selection):
        if selection:
            self.callback(selection[0])
        self.dismiss()

# --- Définition des widgets et onglets ---
class MainTabbedPanel(BoxLayout):
    flash_tab_text = StringProperty("")
    sideload_tab_text = StringProperty("")
    custom_tab_text = StringProperty("")
    udev_tab_text = StringProperty("")
    settings_tab_text = StringProperty("")
    help_tab_text = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: self.update_texts(), 0)
    
    def update_texts(self):
        app = App.get_running_app()
        self.flash_tab_text = app.t("flash_tab")
        self.sideload_tab_text = app.t("sideload_tab")
        self.custom_tab_text = app.t("custom_tab")
        self.udev_tab_text = app.t("udev_tab")
        self.settings_tab_text = app.t("settings_tab")
        self.help_tab_text = app.t("help_tab")
        for child in self.children:
            if hasattr(child, "update_texts"):
                child.update_texts()

class SettingsTab(BoxLayout):
    lang = StringProperty(current_lang)
    colors_applied_text = StringProperty("")
    title_text = StringProperty("")
    interface_color_text = StringProperty("")
    log_color_text = StringProperty("")
    text_color_text = StringProperty("")
    language_text = StringProperty("")
    
    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.update_texts(), 0)
        self.ids.lang_spinner.bind(text=self.on_lang_change)
    
    def on_lang_change(self, spinner, new_lang):
        App.get_running_app().update_translations(new_lang)
    
    def apply_settings(self):
        settings = {
            "interface_color": self.ids.interface_picker.color,
            "log_color": self.ids.log_picker.color,
            "text_color": self.ids.text_picker.color,
            "lang": self.ids.lang_spinner.text,
            "disable_theme": self.ids.disable_theme_checkbox.active
        }
        save_settings(settings)
        App.get_running_app().update_theme(settings)
        App.get_running_app().update_translations(settings["lang"])
    
    def apply_translation(self):
        App.get_running_app().update_translations(self.ids.lang_spinner.text)
    
    def update_texts(self):
        app = App.get_running_app()
        self.title_text = app.t("settings")
        self.interface_color_text = app.t("interface_color")
        self.log_color_text = app.t("log_color")
        self.text_color_text = app.t("text_color")
        self.language_text = app.t("language")
        self.colors_applied_text = app.t("colors_applied")
        self.lang = current_lang
        # Mettre à jour l'état de la checkbox à partir des paramètres sauvegardés
        settings = load_settings()
        self.ids.disable_theme_checkbox.active = settings.get("disable_theme", False)

class HelpTab(BoxLayout):
    help_text = StringProperty("")
    
    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.update_texts(), 0)
    
    def update_texts(self):
        app = App.get_running_app()
        self.help_text = app.t("help_instructions")

class FlashCustomOSTab(BoxLayout):
    instructions = StringProperty("")
    
    def on_kv_post(self, base_widget):
        self.update_texts()
    
    def update_texts(self):
        if current_lang == "fr":
            self.instructions = translations_dict["fr"].get("custom_os_instructions")
        else:
            self.instructions = translations_dict["en"].get("custom_os_instructions")

class DiagnosticTab(BoxLayout):
    pass

class FlashTab(BoxLayout):
    device_status_text = StringProperty("")
    device_status_color = ListProperty([1, 0, 0, 1])
    partition_text = StringProperty("")
    slot_text = StringProperty("")
    no_slot_text = StringProperty("")
    slot_a_text = StringProperty("")
    slot_b_text = StringProperty("")
    browse_text = StringProperty("")
    flash_text = StringProperty("")
    reboot_text = StringProperty("")
    lock_bootloader_text = StringProperty("")
    unlock_bootloader_text = StringProperty("")
    fastboot_getvar_text = StringProperty("")
    clear_log_text = StringProperty("")
    save_log_text = StringProperty("")
    
    def on_kv_post(self, base_widget):
        Clock.schedule_interval(self.check_device_status, 5)
        Clock.schedule_once(lambda dt: self.update_texts(), 0)
    
    def check_device_status(self, dt):
        try:
            adb_output = subprocess.run("adb devices", shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, universal_newlines=True, timeout=2)
            adb_lines = adb_output.stdout.strip().splitlines()
            adb_devices = [line for line in adb_lines[1:] if line.strip() and "device" in line]
        except Exception:
            adb_devices = []
        try:
            fastboot_output = subprocess.run("fastboot devices", shell=True, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, universal_newlines=True, timeout=2)
            fastboot_lines = fastboot_output.stdout.strip().splitlines()
            fastboot_devices = [line for line in fastboot_lines if line.strip()]
        except Exception:
            fastboot_devices = []
        app = App.get_running_app()
        if adb_devices:
            self.device_status_text = app.t("device_adb_connected")
            self.device_status_color = [0, 1, 0, 1]
        elif fastboot_devices:
            self.device_status_text = app.t("device_fastboot_connected")
            self.device_status_color = [0, 1, 0, 1]
        else:
            self.device_status_text = app.t("no_device")
            self.device_status_color = [1, 0, 0, 1]
    
    def open_filechooser(self):
        popup = FileChooserPopup(self.file_selected, ".zip")
        popup.open()
    
    def file_selected(self, filename):
        self.log("File selected: " + filename)
    
    def flash_device(self):
        app = App.get_running_app()
        self.log(app.t("flash_started"))
        threading.Thread(target=run_command_realtime, args=("echo " + app.t("echo_flashing"), self.log)).start()
    
    def reboot_device(self):
        app = App.get_running_app()
        threading.Thread(target=run_command_realtime, args=("echo " + app.t("echo_rebooting"), self.log)).start()
    
    def lock_bootloader(self):
        app = App.get_running_app()
        self.log(app.t("attempt_lock"))
        threading.Thread(target=run_command_realtime, args=("fastboot oem lock", self.log)).start()
        threading.Thread(target=run_command_realtime, args=("fastboot flashing lock", self.log)).start()
    
    def unlock_bootloader(self):
        app = App.get_running_app()
        self.log(app.t("attempt_unlock"))
        threading.Thread(target=run_command_realtime, args=("fastboot oem unlock", self.log)).start()
        threading.Thread(target=run_command_realtime, args=("fastboot flashing unlock", self.log)).start()
    
    def getvar_device(self):
        threading.Thread(target=run_command_realtime, args=("fastboot getvar all", self.log)).start()
    
    def adb_reboot_bootloader(self):
        app = App.get_running_app()
        threading.Thread(target=run_command_realtime, args=(app.t("adb_reboot_bootloader"), self.log)).start()
    
    def adb_reboot_recovery(self):
        app = App.get_running_app()
        threading.Thread(target=run_command_realtime, args=(app.t("adb_reboot_recovery"), self.log)).start()
    
    def log_clear(self):
        if self.ids.get("flash_log"):
            Clock.schedule_once(lambda dt: setattr(self.ids.flash_log, 'text', ""))
    
    def log_save(self):
        if self.ids.get("flash_log"):
            with open("flash_log.txt", "w", encoding="utf-8") as f:
                f.write(self.ids.flash_log.text)
    
    def log(self, message):
        if self.ids.get("flash_log"):
            Clock.schedule_once(lambda dt, m=message: setattr(self.ids.flash_log, 'text', self.ids.flash_log.text + m + "\n"))
    
    def update_texts(self):
        app = App.get_running_app()
        self.device_status_text = app.t("no_device")
        self.partition_text = app.t("menu_partition")
        self.slot_text = app.t("choose_slot")
        self.no_slot_text = app.t("no_slot")
        self.slot_a_text = app.t("slot_a")
        self.slot_b_text = app.t("slot_b")
        self.browse_text = app.t("browse")
        self.flash_text = app.t("flash")
        self.reboot_text = app.t("reboot")
        self.lock_bootloader_text = app.t("lock_bootloader")
        self.unlock_bootloader_text = app.t("unlock_bootloader")
        self.fastboot_getvar_text = app.t("fastboot_getvar")
        self.clear_log_text = app.t("clear_log")
        self.save_log_text = app.t("save_log")

class SideloadTab(BoxLayout):
    browse_text = StringProperty("")
    sideload_text = StringProperty("")
    clear_log_text = StringProperty("")
    save_log_text = StringProperty("")
    
    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.update_texts(), 0)
    
    def open_filechooser(self):
        popup = FileChooserPopup(self.file_selected, ".zip")
        popup.open()
    
    def file_selected(self, filename):
        self.log("File selected: " + filename)
    
    def execute_sideload(self):
        app = App.get_running_app()
        self.log(app.t("echo_sideload"))
        command = self.ids.sideload_mode_spinner.text + " package.zip"
        threading.Thread(target=run_command_realtime, args=(command, self.log)).start()
    
    def log_clear(self):
        if self.ids.get("sideload_log"):
            Clock.schedule_once(lambda dt: setattr(self.ids.sideload_log, 'text', ""))
    
    def log_save(self):
        if self.ids.get("sideload_log"):
            with open("sideload_log.txt", "w", encoding="utf-8") as f:
                f.write(self.ids.sideload_log.text)
    
    def log(self, message):
        if self.ids.get("sideload_log"):
            Clock.schedule_once(lambda dt, m=message: setattr(self.ids.sideload_log, 'text', self.ids.sideload_log.text + m + "\n"))
    
    def update_texts(self):
        app = App.get_running_app()
        self.browse_text = app.t("browse")
        self.sideload_text = app.t("sideload")
        self.clear_log_text = app.t("clear_log")
        self.save_log_text = app.t("save_log")

class UdevTab(BoxLayout):
    def execute_lsusb(self):
        threading.Thread(target=run_command_realtime, args=("lsusb", self.log)).start()
    
    def apply_udev_rules(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=App.get_running_app().t("sudo_prompt")))
        popup = Popup(title=App.get_running_app().t("confirmation"), content=content, size_hint=(0.8, 0.4))
        def on_dismiss(instance):
            threading.Thread(target=run_command_realtime, args=("sudo cp 99-android.rules /etc/udev/rules.d/", self.log)).start()
        popup.bind(on_dismiss=on_dismiss)
        popup.open()
    
    def install_dependencies(self):
        threading.Thread(target=run_command_realtime, args=("sudo apt-get install android-tools-adb android-tools-fastboot", self.log)).start()
    
    def log(self, message):
        if self.ids.get("udev_log"):
            Clock.schedule_once(lambda dt, m=message: setattr(self.ids.udev_log, 'text', self.ids.udev_log.text + m + "\n"))
    
    def update_texts(self):
        pass

KV = '''
#:kivy 2.2.0
<Button>:
    background_normal: ''
    background_color: 0.05, 0.05, 0.05, 0.8
    color: 0, 1, 1, 1
    font_size: '12sp'

<MainTabbedPanel>:
    canvas.before:
        Color:
            rgba: app.theme_interface_color if not app.disable_theme else [1,1,1,1]
        Rectangle:
            pos: self.pos
            size: self.size
        # Effet cyberpunk (cercle néon)
        Color:
            rgba: (0, 1, 1, 0.2) if not app.disable_theme else (0, 0, 0, 0)
        Ellipse:
            pos: self.center_x - 150, self.center_y - 150
            size: 300, 300
    TabbedPanel:
        do_default_tab: False
        TabbedPanelItem:
            text: app.t("flash_tab")
            FlashTab:
                id: flash_tab
        TabbedPanelItem:
            text: app.t("sideload_tab")
            SideloadTab:
                id: sideload_tab
        TabbedPanelItem:
            text: app.t("custom_tab")
            FlashCustomOSTab:
                id: custom_tab
        TabbedPanelItem:
            text: app.t("udev_tab")
            UdevTab:
                id: udev_tab
        TabbedPanelItem:
            text: app.t("settings_tab")
            SettingsTab:
                id: settings_tab
        TabbedPanelItem:
            text: app.t("help_tab")
            HelpTab:
                id: help_tab
        TabbedPanelItem:
            text: app.t("diagnostic_tab")
            DiagnosticTab:
                id: diag_tab

<LogWidget@TextInput>:
    readonly: True
    multiline: True
    font_size: 12
    background_color: app.theme_log_color
    foreground_color: app.theme_text_color
    padding: [10, 10, 10, 10]
    size_hint_y: None
    height: self.minimum_height

<FileChooserPopup>:
    title: root.popup_title
    size_hint: 0.9, 0.9
    BoxLayout:
        orientation: 'vertical'
        spacing: 5
        padding: 10
        FileChooserListView:
            id: filechooser
            filters: [root.file_filter]
        BoxLayout:
            size_hint_y: 0.1
            spacing: 5
            Button:
                text: root.popup_title
                on_release: root.select_file(filechooser.selection)
            Button:
                text: app.t("cancel")
                on_release: root.dismiss()

<SettingsTab>:
    orientation: 'vertical'
    spacing: 10
    padding: 10
    Label:
        text: root.title_text
        size_hint_y: 0.1
        color: app.theme_text_color
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.6
        Label:
            text: root.interface_color_text
            size_hint_y: 0.1
            color: app.theme_text_color
        ColorPicker:
            id: interface_picker
            size_hint_y: 0.3
        Label:
            text: root.log_color_text
            size_hint_y: 0.1
            color: app.theme_text_color
        ColorPicker:
            id: log_picker
            size_hint_y: 0.3
        Label:
            text: root.text_color_text
            size_hint_y: 0.1
            color: app.theme_text_color
        ColorPicker:
            id: text_picker
            size_hint_y: 0.3
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Label:
            text: root.language_text
            size_hint_x: 0.4
            color: app.theme_text_color
        Spinner:
            id: lang_spinner
            text: root.lang
            values: ['fr','en']
            size_hint_x: 0.6
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        CheckBox:
            id: disable_theme_checkbox
            active: False
        Label:
            text: app.t("disable_theme")
            color: app.theme_text_color
    Button:
        text: app.t("apply_translation")
        size_hint_y: 0.15
        on_release: root.apply_translation()
    Button:
        text: root.colors_applied_text
        size_hint_y: 0.15
        on_release: root.apply_settings()

<HelpTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    ScrollView:
        Label:
            id: help_label
            text: root.help_text
            markup: True
            size_hint_y: None
            height: self.texture_size[1]
            color: app.theme_text_color

<FlashCustomOSTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    ScrollView:
        Label:
            id: custom_label
            text: root.instructions
            markup: True
            size_hint_y: None
            height: self.texture_size[1]
            color: app.theme_text_color

<DiagnosticTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    Label:
        text: app.t("diagnostic_history")
        size_hint_y: 0.1
        color: app.theme_text_color
    ScrollView:
        LogWidget:
            id: diag_log

<FlashTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    BoxLayout:
        size_hint_y: 0.1
        Label:
            id: device_status
            text: root.device_status_text
            color: root.device_status_color
    BoxLayout:
        size_hint_y: 0.1
        spacing: 5
        Spinner:
            id: partition_spinner
            text: root.partition_text
            values: ["boot", "recovery", "vendor", "vendor_boot", "init_boot", "system", "vbmeta", "vendor_kernel", "vendor_kernel_boot", "ramdisk", "tee", "dtbo"]
        Spinner:
            id: slot_spinner
            text: root.slot_text
            values: [root.no_slot_text, root.slot_a_text, root.slot_b_text]
    BoxLayout:
        size_hint_y: 0.1
        spacing: 5
        Button:
            text: root.browse_text
            on_release: root.open_filechooser()
        Button:
            text: root.flash_text
            on_release: root.flash_device()
        Button:
            text: root.reboot_text
            on_release: root.reboot_device()
        Button:
            text: root.lock_bootloader_text
            on_release: root.lock_bootloader()
        Button:
            text: root.unlock_bootloader_text
            on_release: root.unlock_bootloader()
        Button:
            text: root.fastboot_getvar_text
            on_release: root.getvar_device()
        Button:
            text: app.t("clear_log")
            on_release: root.log_clear()
        Button:
            text: app.t("save_log")
            on_release: root.log_save()
    BoxLayout:
        size_hint_y: 0.1
        spacing: 5
        Button:
            text: app.t("adb_reboot_bootloader")
            on_release: root.adb_reboot_bootloader()
        Button:
            text: app.t("adb_reboot_recovery")
            on_release: root.adb_reboot_recovery()
    ScrollView:
        size_hint_y: 0.3
        LogWidget:
            id: flash_log

<SideloadTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    BoxLayout:
        size_hint_y: 0.1
        spacing: 5
        Label:
            text: app.t("sideload_mode")
            size_hint_x: 0.4
            color: app.theme_text_color
        Spinner:
            id: sideload_mode_spinner
            text: "adb -b sideload"
            values: ["adb -a sideload", "adb -b sideload"]
            size_hint_x: 0.6
    BoxLayout:
        size_hint_y: 0.1
        spacing: 5
        Button:
            text: root.browse_text
            on_release: root.open_filechooser()
        Button:
            text: root.sideload_text
            on_release: root.execute_sideload()
        Button:
            text: root.clear_log_text
            on_release: root.log_clear()
        Button:
            text: root.save_log_text
            on_release: root.log_save()
    ScrollView:
        size_hint_y: 0.4
        do_scroll_x: True
        do_scroll_y: True
        LogWidget:
            id: sideload_log

<UdevTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    Label:
        text: app.t("udev_tab")
        size_hint_y: 0.1
        color: app.theme_text_color
    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: 0.1
        spacing: 5
        Label:
            text: "idVendor:"
            size_hint_x: 0.3
            color: app.theme_text_color
        TextInput:
            id: idVendor_input
            multiline: False
        Label:
            text: "idProduct:"
            size_hint_x: 0.3
            color: app.theme_text_color
        TextInput:
            id: idProduct_input
            multiline: False
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Button:
            text: app.t("execute_lsusb")
            on_release: root.execute_lsusb()
        Button:
            text: app.t("udev_tab")
            on_release: root.apply_udev_rules()
        Button:
            text: app.t("install_dependencies")
            on_release: root.install_dependencies()
    ProgressBar:
        id: progress_bar
        max: 100
        value: 0
        size_hint_y: 0.1
    ScrollView:
        size_hint_y: 0.4
        do_scroll_x: True
        do_scroll_y: True
        LogWidget:
            id: udev_log
'''
Builder.load_string(KV)

# --- Classe principale de l'application ---
class MainApp(App):
    theme_interface_color = ListProperty([0.1, 0.1, 0.1, 1])
    theme_log_color = ListProperty([0.0, 0.0, 0.0, 1])
    theme_text_color = ListProperty([0, 1, 1, 1])
    disable_theme = BooleanProperty(False)
    
    def build(self):
        settings = load_settings()
        self.update_theme(settings)
        self.update_translations(settings.get("lang", "fr"))
        return MainTabbedPanel()
    
    def update_theme(self, settings):
        self.disable_theme = settings.get("disable_theme", False)
        if self.disable_theme:
            self.theme_interface_color = [1, 1, 1, 1]
            self.theme_log_color = [1, 1, 1, 1]
            self.theme_text_color = [0, 0, 0, 1]
            Window.clearcolor = self.theme_interface_color
        else:
            self.theme_interface_color = settings.get("interface_color", [0.1, 0.1, 0.1, 1])
            self.theme_log_color = settings.get("log_color", [0.0, 0.0, 0.0, 1])
            self.theme_text_color = settings.get("text_color", [0, 1, 1, 1])
            Window.clearcolor = self.theme_interface_color
    
    def update_translations(self, new_lang):
        global current_lang
        current_lang = new_lang
        if self.root and hasattr(self.root, "update_texts"):
            self.root.update_texts()
    
    def t(self, key):
        return translations_dict[current_lang].get(key, key)

if __name__ == '__main__':
    MainApp().run()
