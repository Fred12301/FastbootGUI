import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile
import tempfile
import shutil


class FastbootFlashTool:
    def __init__(self, root):
        self.root = root

        # Dictionnaire de traductions
        self.translations = {
            "fr": {
                "title": "Outil Flash Fastboot",
                "flash_tab": "Flash",
                "terminal_tab": "Terminal",
                "settings_tab": "Paramètres",
                "readme_tab": "README",
                "device_status": "Statut de l'appareil",
                "check_status": "Vérifier le statut",
                "file_to_flash": "Fichier à flasher",
                "browse": "Parcourir",
                "select_partition": "Sélectionner la partition",
                "slot_optional": "Slot (optionnel):",
                "flash": "Flasher",
                "reboot": "Redémarrer",
                "wipe_partition": "Effacer la partition",
                "temporary_boot": "Démarrage Temporaire",
                "firmware_flash": "Flash Firmware",
                "select_firmware_files": "Sélectionner les fichiers firmware",
                "unlock_bootloader": "Unlock Bootloader",
                "lock_bootloader": "Lock Bootloader",
                "logs": "Logs",
                "terminal_label": "Émulateur de Terminal\n(Entrez une commande et cliquez sur 'Exécuter')",
                "execute": "Exécuter",
                "settings_label": "Paramètres - Personnalisez votre interface",
                "theme": "Thème",
                "light": "Clair",
                "dark": "Sombre",
                "log_background": "Fond de Log",
                "default": "Par défaut",
                "black": "Noir",
                "language": "Langue",
                "french": "Français",
                "english": "Anglais",
                "readme_info": "Informations & Aide",
                "help_title": "Aide - Outil Flash Fastboot",
                "help_text": (
                    "Bienvenue dans l'Outil Flash Fastboot !\n\n"
                    "Onglet Flash :\n"
                    "  - Vérifiez le statut de l'appareil avec 'Vérifier le statut'.\n"
                    "  - Sélectionnez un fichier .img à flasher ou plusieurs fichiers firmware (.img, .zip, .md5).\n"
                    "  - Choisissez la partition cible (boot, recovery, bootloader, vbmeta, vendor, system, etc.).\n"
                    "  - Vous pouvez éventuellement spécifier un slot (a/b).\n"
                    "  - Actions disponibles : Flasher, Redémarrer, Effacer la partition, Démarrage Temporaire,\n"
                    "    Unlock Bootloader, Lock Bootloader.\n\n"
                    "Firmware Flash Option :\n"
                    "  - Sélectionnez directement un ou plusieurs fichiers firmware avec extension .img, .zip ou .md5.\n"
                    "  - Pour les .zip, le programme extraira les images contenues et les flashera.\n\n"
                    "Onglet Terminal :\n"
                    "  - Utilisez l'émulateur pour exécuter des commandes sur votre PC.\n\n"
                    "Onglet Paramètres :\n"
                    "  - Changez le thème (Clair/Sombre), le fond des logs et la langue.\n\n"
                    "Assurez-vous que votre appareil est en mode fastboot et que fastboot est installé et accessible."
                )
            },
            "en": {
                "title": "Fastboot Flash Tool",
                "flash_tab": "Flash",
                "terminal_tab": "Terminal",
                "settings_tab": "Settings",
                "readme_tab": "README",
                "device_status": "Device Status",
                "check_status": "Check Status",
                "file_to_flash": "File to Flash",
                "browse": "Browse",
                "select_partition": "Select Partition",
                "slot_optional": "Slot (optional):",
                "flash": "Flash",
                "reboot": "Reboot",
                "wipe_partition": "Wipe Partition",
                "temporary_boot": "Temporary Boot",
                "firmware_flash": "Flash Firmware",
                "select_firmware_files": "Select Firmware Files",
                "unlock_bootloader": "Unlock Bootloader",
                "lock_bootloader": "Lock Bootloader",
                "logs": "Logs",
                "terminal_label": "Terminal Emulator\n(Enter command and click 'Execute')",
                "execute": "Execute",
                "settings_label": "Settings - Customize your interface",
                "theme": "Theme",
                "light": "Light",
                "dark": "Dark",
                "log_background": "Log Background",
                "default": "Default",
                "black": "Black",
                "language": "Language",
                "french": "French",
                "english": "English",
                "readme_info": "Information & Help",
                "help_title": "Help - Fastboot Flash Tool",
                "help_text": (
                    "Welcome to Fastboot Flash Tool!\n\n"
                    "Flash Tab:\n"
                    "  - Check device status using 'Check Status'.\n"
                    "  - Browse and select a .img file to flash or multiple firmware files (.img, .zip, .md5).\n"
                    "  - Choose the target partition (e.g., boot, recovery, bootloader, vbmeta, vendor, system, etc.).\n"
                    "  - Optionally specify a slot (a/b).\n"
                    "  - Available actions: Flash, Reboot, Wipe Partition, Temporary Boot,\n"
                    "    Unlock Bootloader, Lock Bootloader.\n\n"
                    "Firmware Flash Option:\n"
                    "  - Directly select one or several firmware files with extension .img, .zip, or .md5.\n"
                    "  - For .zip files, the tool will extract any contained .img files and flash them.\n\n"
                    "Terminal Tab:\n"
                    "  - Use the terminal emulator to run commands on your PC.\n\n"
                    "Settings Tab:\n"
                    "  - Change the interface theme (Light/Dark), log background color, and language.\n\n"
                    "Ensure your device is in fastboot mode and that fastboot is installed and in your PATH."
                )
            }
        }

        # Options variables
        self.theme = tk.StringVar(value="light")
        self.lang = tk.StringVar(value="fr")
        self.log_bg_option = tk.StringVar(value="default")

        # Liste des partitions disponibles
        self.partitions = [
            "boot", "recovery", "bootloader", "vbmeta", "vendor",
            "system", "system_a", "system_b",
            "dtbo", "radio", "modem",
            "cache", "userdata", "metadata",
            "persist", "misc", "splash",
            "firmware"
        ]

        # Statut de la connexion et fichiers firmware sélectionnés
        self.device_status = tk.StringVar(value="Inactive")
        self.firmware_files = []

        # Configuration du style ttk
        self.style = ttk.Style()

        # Paramétrage de la fenêtre principale (adapté pour un petit écran)
        self.root.title(self.translations[self.lang.get()]["title"])
        self.root.geometry("1250x700")
        self.root.resizable(False, False)

        # Création du Notebook et des onglets
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_frame = ttk.Frame(self.notebook)
        self.terminal_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.readme_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.main_frame, text=self.translations[self.lang.get()]["flash_tab"])
        self.notebook.add(self.terminal_frame, text=self.translations[self.lang.get()]["terminal_tab"])
        self.notebook.add(self.settings_frame, text=self.translations[self.lang.get()]["settings_tab"])
        self.notebook.add(self.readme_frame, text=self.translations[self.lang.get()]["readme_tab"])

        # Construction des onglets
        self.create_main_frame()
        self.create_terminal_frame()
        self.create_settings_frame()
        self.create_readme_frame()
        self.create_help_button()

        # Actualisation des textes selon la langue
        self.update_language_texts()

        # Application du thème après création des zones de log
        self.apply_theme()

    # ---------------------------
    # Mise à jour des textes (langue)
    # ---------------------------
    def update_language_texts(self):
        trans = self.translations[self.lang.get()]
        self.root.title(trans["title"])
        self.notebook.tab(self.main_frame, text=trans["flash_tab"])
        self.notebook.tab(self.terminal_frame, text=trans["terminal_tab"])
        self.notebook.tab(self.settings_frame, text=trans["settings_tab"])
        self.notebook.tab(self.readme_frame, text=trans["readme_tab"])

        self.status_frame.configure(text=trans["device_status"])
        self.file_frame.configure(text=trans["file_to_flash"])
        self.partition_frame.configure(text=trans["select_partition"])
        self.action_frame.configure(text=trans["flash_tab"] + " / Actions")
        self.firmware_frame.configure(text=trans["firmware_flash"])
        self.log_frame.configure(text=trans["logs"])

        self.check_status_button.config(text=trans["check_status"])
        self.browse_button.config(text=trans["browse"])
        self.slot_label.config(text=trans["slot_optional"])
        self.flash_button.config(text=trans["flash"])
        self.reboot_button.config(text=trans["reboot"])
        self.wipe_button.config(text=trans["wipe_partition"])
        self.boot_temp_button.config(text=trans["temporary_boot"])
        self.firmware_select_button.config(text=trans["select_firmware_files"])
        self.firmware_flash_button.config(text=trans["firmware_flash"])
        self.unlock_button.config(text=trans["unlock_bootloader"])
        self.lock_button.config(text=trans["lock_bootloader"])

        self.terminal_label.config(text=trans["terminal_label"])
        self.execute_terminal_button.config(text=trans["execute"])

        self.settings_label.config(text=trans["settings_label"])
        self.theme_frame.configure(text=trans["theme"])
        self.log_frame_setting.configure(text=trans["log_background"])
        self.lang_frame.configure(text=trans["language"])
        self.radio_theme_light.config(text=trans["light"])
        self.radio_theme_dark.config(text=trans["dark"])
        self.radio_log_default.config(text=trans["default"])
        self.radio_log_black.config(text=trans["black"])
        self.radio_lang_fr.config(text=trans["french"])
        self.radio_lang_en.config(text=trans["english"])

        self.readme_label.config(text=trans["readme_info"])

    # ---------------------------
    # Thème et langue
    # ---------------------------
    def apply_theme(self):
        theme = self.theme.get()
        if theme == "light":
            bg_color = "white"
            fg_color = "black"
            root_bg = "white"
            log_bg = "white"
            self.style.theme_use('clam')
        else:
            bg_color = "gray20"
            fg_color = "white"
            root_bg = "gray20"
            log_bg = "black"
            self.style.theme_use('alt')

        self.style.configure('.', background=bg_color, foreground=fg_color)
        self.style.configure('TLabel', background=bg_color, foreground=fg_color)
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        self.style.configure('TButton', background=bg_color, foreground=fg_color)

        self.root.config(bg=root_bg)
        if hasattr(self, "log_text"):
            self.log_text.config(bg=log_bg, fg=fg_color, insertbackground=fg_color)
        self.log(f"Thème changé en {self.theme.get().capitalize()}.")

    def apply_log_color(self):
        option = self.log_bg_option.get()
        if option == "default":
            if self.theme.get() == "light":
                self.log_text.config(bg="white", fg="black", insertbackground="black")
            else:
                self.log_text.config(bg="black", fg="white", insertbackground="white")
            self.log("Fond de log remis par défaut.")
        elif option == "black":
            self.log_text.config(bg="black", fg="white", insertbackground="white")
            self.log("Fond de log défini sur Noir.")

    def apply_language(self):
        self.log(f"Langue changée en {'Français' if self.lang.get() == 'fr' else 'English'}.")
        self.update_language_texts()

    # ---------------------------
    # Zone de log (avec scrollbar)
    # ---------------------------
    def log(self, message):
        if hasattr(self, "log_text"):
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.config(state="disabled")
            self.log_text.see("end")

    # ---------------------------
    # Onglet Flash (Main Frame)
    # ---------------------------
    def create_main_frame(self):
        # Statut de l'appareil
        self.status_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["device_status"],
            padding=(10, 10)
        )
        self.status_frame.pack(fill="x", padx=10, pady=5)
        self.status_label = tk.Label(self.status_frame, textvariable=self.device_status, bg="red", fg="white", width=10, anchor="center")
        self.status_label.pack(side="left", padx=5, pady=5)
        self.check_status_button = ttk.Button(
            self.status_frame,
            text=self.translations[self.lang.get()]["check_status"],
            command=self.check_device_status
        )
        self.check_status_button.pack(side="left", padx=5, pady=5)

        # Fichier à flasher (flash partition)
        self.file_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["file_to_flash"],
            padding=(10, 10)
        )
        self.file_frame.pack(fill="x", padx=10, pady=5)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, width=80)
        self.file_entry.pack(side="left", padx=5, pady=5)
        self.browse_button = ttk.Button(
            self.file_frame,
            text=self.translations[self.lang.get()]["browse"],
            command=self.browse_file
        )
        self.browse_button.pack(side="left", padx=5, pady=5)

        # Sélection de partition
        self.partition_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["select_partition"],
            padding=(10, 10)
        )
        self.partition_frame.pack(fill="x", padx=10, pady=5)
        self.partition_var = tk.StringVar(value=self.partitions[0])
        self.partition_menu = ttk.Combobox(
            self.partition_frame,
            textvariable=self.partition_var,
            values=self.partitions,
            state="readonly"
        )
        self.partition_menu.pack(fill="x", padx=5, pady=5)

        # Actions (flash, reboot, wipe, boot temp)
        self.action_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["flash_tab"] + " / Actions",
            padding=(10, 10)
        )
        self.action_frame.pack(fill="x", padx=10, pady=5)
        action_subframe = ttk.Frame(self.action_frame)
        action_subframe.pack(fill="x")
        self.slot_label = ttk.Label(action_subframe, text=self.translations[self.lang.get()]["slot_optional"])
        self.slot_label.pack(side="left", padx=5)
        self.slot_var = tk.StringVar(value="")
        self.slot_menu = ttk.Combobox(action_subframe, textvariable=self.slot_var, values=["", "a", "b"], state="readonly", width=5)
        self.slot_menu.pack(side="left", padx=5)
        self.flash_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["flash"],
            command=self.start_flash_thread
        )
        self.flash_button.pack(side="left", padx=5)
        self.reboot_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["reboot"],
            command=self.reboot_device
        )
        self.reboot_button.pack(side="left", padx=5)
        self.wipe_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["wipe_partition"],
            command=self.confirm_wipe_partition
        )
        self.wipe_button.pack(side="left", padx=5)
        self.boot_temp_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["temporary_boot"],
            command=self.boot_temp_image
        )
        self.boot_temp_button.pack(side="left", padx=5)
        # Boutons pour Unlock et Lock Bootloader
        self.unlock_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["unlock_bootloader"],
            command=self.unlock_bootloader
        )
        self.unlock_button.pack(side="left", padx=5)
        self.lock_button = ttk.Button(
            action_subframe,
            text=self.translations[self.lang.get()]["lock_bootloader"],
            command=self.lock_bootloader
        )
        self.lock_button.pack(side="left", padx=5)

        # Section Flash Firmware (sélection de fichiers firmware)
        self.firmware_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["firmware_flash"],
            padding=(10, 10)
        )
        self.firmware_frame.pack(fill="x", padx=10, pady=5)
        self.firmware_select_button = ttk.Button(
            self.firmware_frame,
            text=self.translations[self.lang.get()]["select_firmware_files"],
            command=self.select_firmware_files
        )
        self.firmware_select_button.pack(side="left", padx=5)
        self.firmware_flash_button = ttk.Button(
            self.firmware_frame,
            text=self.translations[self.lang.get()]["firmware_flash"],
            command=self.flash_firmware
        )
        self.firmware_flash_button.pack(side="left", padx=5)

        # Zone de log (avec scrollbar)
        self.log_frame = ttk.LabelFrame(
            self.main_frame,
            text=self.translations[self.lang.get()]["logs"],
            padding=(10, 10)
        )
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text = tk.Text(self.log_frame, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.log_scrollbar = tk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        self.log_scrollbar.pack(side="right", fill="y")

    # ---------------------------
    # Onglet Terminal
    # ---------------------------
    def create_terminal_frame(self):
        self.terminal_label = ttk.Label(self.terminal_frame, text=self.translations[self.lang.get()]["terminal_label"])
        self.terminal_label.pack(pady=10)
        self.terminal_input = tk.Text(self.terminal_frame, height=5, bg="black", fg="white", insertbackground="white")
        self.terminal_input.pack(fill="x", padx=10, pady=10)
        self.execute_terminal_button = ttk.Button(
            self.terminal_frame,
            text=self.translations[self.lang.get()]["execute"],
            command=self.execute_terminal_command
        )
        self.execute_terminal_button.pack(pady=5)

    def execute_terminal_command(self):
        command = self.terminal_input.get("1.0", "end").strip()
        if not command:
            self.log("Erreur : aucune commande spécifiée.")
            return

        def run_command():
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                self.log(result.stdout)
                if result.stderr:
                    self.log(result.stderr)
            except Exception as e:
                self.log(f"Erreur lors de l'exécution : {str(e)}")

        threading.Thread(target=run_command, daemon=True).start()

    # ---------------------------
    # Onglet Paramètres
    # ---------------------------
    def create_settings_frame(self):
        self.settings_label = ttk.Label(self.settings_frame, text=self.translations[self.lang.get()]["settings_label"])
        self.settings_label.pack(pady=10)
        self.theme_frame = ttk.LabelFrame(
            self.settings_frame,
            text=self.translations[self.lang.get()]["theme"],
            padding=(10, 10)
        )
        self.theme_frame.pack(fill="x", padx=10, pady=5)
        self.radio_theme_light = ttk.Radiobutton(
            self.theme_frame,
            text=self.translations[self.lang.get()]["light"],
            variable=self.theme, value="light",
            command=self.on_theme_change
        )
        self.radio_theme_light.pack(anchor="w", padx=5, pady=5)
        self.radio_theme_dark = ttk.Radiobutton(
            self.theme_frame,
            text=self.translations[self.lang.get()]["dark"],
            variable=self.theme, value="dark",
            command=self.on_theme_change
        )
        self.radio_theme_dark.pack(anchor="w", padx=5, pady=5)
        self.log_frame_setting = ttk.LabelFrame(
            self.settings_frame,
            text=self.translations[self.lang.get()]["log_background"],
            padding=(10, 10)
        )
        self.log_frame_setting.pack(fill="x", padx=10, pady=5)
        self.radio_log_default = ttk.Radiobutton(
            self.log_frame_setting,
            text=self.translations[self.lang.get()]["default"],
            variable=self.log_bg_option, value="default",
            command=self.apply_log_color
        )
        self.radio_log_default.pack(anchor="w", padx=5, pady=5)
        self.radio_log_black = ttk.Radiobutton(
            self.log_frame_setting,
            text=self.translations[self.lang.get()]["black"],
            variable=self.log_bg_option, value="black",
            command=self.apply_log_color
        )
        self.radio_log_black.pack(anchor="w", padx=5, pady=5)
        self.lang_frame = ttk.LabelFrame(
            self.settings_frame,
            text=self.translations[self.lang.get()]["language"],
            padding=(10, 10)
        )
        self.lang_frame.pack(fill="x", padx=10, pady=5)
        self.radio_lang_fr = ttk.Radiobutton(
            self.lang_frame,
            text=self.translations[self.lang.get()]["french"],
            variable=self.lang, value="fr",
            command=self.apply_language
        )
        self.radio_lang_fr.pack(anchor="w", padx=5, pady=5)
        self.radio_lang_en = ttk.Radiobutton(
            self.lang_frame,
            text=self.translations[self.lang.get()]["english"],
            variable=self.lang, value="en",
            command=self.apply_language
        )
        self.radio_lang_en.pack(anchor="w", padx=5, pady=5)

    # ---------------------------
    # Onglet README
    # ---------------------------
    def create_readme_frame(self):
        self.readme_label = ttk.Label(self.readme_frame, text=self.translations[self.lang.get()]["readme_info"], font=("Arial", 14))
        self.readme_label.pack(pady=10)
        self.readme_text = tk.Text(self.readme_frame, wrap="word")
        self.readme_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.readme_text.insert("1.0", self.translations[self.lang.get()]["help_text"])
        self.readme_text.config(state="disabled")
        self.readme_scrollbar = tk.Scrollbar(self.readme_frame, orient="vertical", command=self.readme_text.yview)
        self.readme_text.configure(yscrollcommand=self.readme_scrollbar.set)
        self.readme_scrollbar.pack(side="right", fill="y")

    # ---------------------------
    # Sélection des fichiers firmware et flash firmware complet
    # ---------------------------
    def select_firmware_files(self):
        files = filedialog.askopenfilenames(
            title=self.translations[self.lang.get()]["select_firmware_files"],
            filetypes=[("Firmware Files", "*.img *.zip *.md5"), ("All Files", "*.*")]
        )
        if files:
            self.firmware_files = list(files)
            self.log(f"{len(self.firmware_files)} fichier(s) firmware sélectionné(s).")
        else:
            self.log("Aucun fichier firmware sélectionné.")

    def flash_firmware(self):
        if not self.firmware_files:
            messagebox.showerror("Erreur", "Aucun fichier firmware sélectionné.")
            return

        def flash_thread():
            self.check_device_status()
            if self.device_status.get() != "Active":
                messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
                return

            for file in self.firmware_files:
                ext = os.path.splitext(file)[1].lower()
                if ext == ".img":
                    partition_name = os.path.splitext(os.path.basename(file))[0]
                    cmd = ["fastboot", "flash", partition_name, file]
                    self.log(f"Flash de {partition_name} avec {file}...")
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        self.log(result.stdout)
                        if result.stderr:
                            self.log(result.stderr)
                    except Exception as e:
                        self.log(f"Erreur lors du flash de {partition_name} : {str(e)}")
                elif ext == ".zip":
                    self.log(f"Extraction du fichier ZIP {file}...")
                    try:
                        with zipfile.ZipFile(file, 'r') as zip_ref:
                            temp_dir = tempfile.mkdtemp()
                            zip_ref.extractall(temp_dir)
                            extracted_imgs = []
                            for root_dir, dirs, files_in_dir in os.walk(temp_dir):
                                for f in files_in_dir:
                                    if f.lower().endswith(".img"):
                                        extracted_imgs.append(os.path.join(root_dir, f))
                            if not extracted_imgs:
                                self.log(f"Aucune image (.img) trouvée dans {os.path.basename(file)}.")
                            else:
                                for img_file in extracted_imgs:
                                    partition_name = os.path.splitext(os.path.basename(img_file))[0]
                                    cmd = ["fastboot", "flash", partition_name, img_file]
                                    self.log(f"Flash de {partition_name} (extrait de {os.path.basename(file)})...")
                                    try:
                                        result = subprocess.run(cmd, capture_output=True, text=True)
                                        self.log(result.stdout)
                                        if result.stderr:
                                            self.log(result.stderr)
                                    except Exception as e:
                                        self.log(f"Erreur lors du flash de {partition_name} : {str(e)}")
                            shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.log(f"Erreur lors de l'extraction du fichier ZIP {os.path.basename(file)} : {str(e)}")
                elif ext == ".md5":
                    self.log(f"Fichier {os.path.basename(file)} (checksum) ignoré.")
            self.log("Processus de flash firmware terminé.")

        threading.Thread(target=flash_thread, daemon=True).start()

    # ---------------------------
    # Méthodes fastboot (flash partition, reboot, wipe, boot temp)
    # ---------------------------
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title=self.translations[self.lang.get()]["file_to_flash"],
            filetypes=[("Fastboot Images", "*.img"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)

    def check_device_status(self):
        try:
            result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True)
            if result.stdout.strip():
                self.device_status.set("Active")
                self.status_label.config(bg="green")
                self.log("Appareil détecté :\n" + result.stdout.strip())
            else:
                self.device_status.set("Inactive")
                self.status_label.config(bg="red")
                self.log("Aucun appareil détecté.")
        except FileNotFoundError:
            self.device_status.set("Inactive")
            self.status_label.config(bg="red")
            self.log("Erreur : fastboot n'est pas installé ou introuvable dans le PATH.")

    def start_flash_thread(self):
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return
        threading.Thread(target=self.flash_partition, daemon=True).start()

    def flash_partition(self):
        partition = self.partition_var.get()
        file_path = self.file_path_var.get()
        slot = self.slot_var.get()
        if not os.path.exists(file_path):
            self.log("Erreur : fichier introuvable.")
            return
        cmd = ["fastboot", "flash", partition]
        if slot:
            cmd.extend(["--slot", slot])
        cmd.append(file_path)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
        except Exception as e:
            self.log(f"Erreur lors du flash : {str(e)}")

    def confirm_wipe_partition(self):
        response = messagebox.askyesno("Attention", "Êtes-vous sûr de vouloir effacer la partition ? Cette action est irréversible.")
        if response:
            self.wipe_partition()

    def wipe_partition(self):
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return
        partition = self.partition_var.get()
        try:
            result = subprocess.run(["fastboot", "erase", partition], capture_output=True, text=True)
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
        except Exception as e:
            self.log(f"Erreur lors de l'effacement de la partition : {str(e)}")

    def reboot_device(self):
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return
        try:
            result = subprocess.run(["fastboot", "reboot"], capture_output=True, text=True)
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
        except Exception as e:
            self.log(f"Erreur lors du redémarrage : {str(e)}")

    def boot_temp_image(self):
        file_path = self.file_path_var.get()
        if not os.path.exists(file_path):
            self.log("Erreur : fichier introuvable.")
            return
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return
        try:
            result = subprocess.run(["fastboot", "boot", file_path], capture_output=True, text=True)
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
        except Exception as e:
            self.log(f"Erreur lors du boot temporaire : {str(e)}")

    # ---------------------------
    # Nouveaux boutons pour Unlock / Lock Bootloader
    # ---------------------------
    def unlock_bootloader(self):
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return

        def run_unlock():
            commands = [["fastboot", "flashing", "unlock"], ["fastboot", "oem", "unlock"]]
            for cmd in commands:
                self.log("Exécution de : " + " ".join(cmd))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    self.log(result.stdout)
                    if result.stderr:
                        self.log(result.stderr)
                except Exception as e:
                    self.log("Erreur lors de l'exécution de " + " ".join(cmd) + " : " + str(e))
            self.log("Opération Unlock Bootloader terminée.")

        threading.Thread(target=run_unlock, daemon=True).start()

    def lock_bootloader(self):
        self.check_device_status()
        if self.device_status.get() != "Active":
            messagebox.showerror("Erreur", "Aucun appareil actif détecté.")
            return

        def run_lock():
            commands = [["fastboot", "flashing", "lock"], ["fastboot", "oem", "lock"]]
            for cmd in commands:
                self.log("Exécution de : " + " ".join(cmd))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    self.log(result.stdout)
                    if result.stderr:
                        self.log(result.stderr)
                except Exception as e:
                    self.log("Erreur lors de l'exécution de " + " ".join(cmd) + " : " + str(e))
            self.log("Opération Lock Bootloader terminée.")

        threading.Thread(target=run_lock, daemon=True).start()

    # ---------------------------
    # Bouton Aide et fenêtre d'aide (avec scrollbar)
    # ---------------------------
    def create_help_button(self):
        help_button = ttk.Button(self.root, text="Aide", command=self.show_help)
        help_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def show_help(self):
        trans = self.translations[self.lang.get()]
        help_window = tk.Toplevel(self.root)
        help_window.title(trans["help_title"])
        help_window.geometry("600x500")
        help_frame = tk.Frame(help_window)
        help_frame.pack(expand=True, fill="both", padx=10, pady=10)
        help_area = tk.Text(help_frame, wrap="word")
        help_area.insert("1.0", trans["help_text"])
        help_area.config(state="disabled")
        help_area.pack(side="left", fill="both", expand=True)
        help_scrollbar = tk.Scrollbar(help_frame, orient="vertical", command=help_area.yview)
        help_area.configure(yscrollcommand=help_scrollbar.set)
        help_scrollbar.pack(side="right", fill="y")

    # Méthode appelée lors d'un changement de thème
    def on_theme_change(self):
        self.apply_theme()
        self.apply_log_color()


if __name__ == "__main__":
    root = tk.Tk()
    app = FastbootFlashTool(root)
    root.mainloop()
