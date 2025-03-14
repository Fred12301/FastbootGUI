# FastbootGUI
Simple GUI for flashing, debugging, unlocking bootloader phone and etc via Fastboot / ADB modes.

## Install
You can download different versions of the GUI in the [Releases tab](https://github.com/Fred12301/FastbootGUI/releases)

## Build
To compile a Python script into an executable on Windows or Linux, you can use PyInstaller.

Here are the detailed steps:

1. **Install [latest python](https://www.python.org/downloads/windows/)**

   (Make sure to add it to PATH during installation)

2. **Install PyInstaller**
   ```shell
   pip install pyinstaller
   ```

3. **Compile the script into an executable**

   Go to the root directory of the repository and compile the desired version of FastbootGUI _(e.g. FastbootGuiMini.py)_
   
   ```shell
   pyinstaller --onefile FastbootGuiMini.py
   ```

This will generate an .exe file in the dist/ folder.

#### Useful options with PyInstaller

- Create an executable without a console (for GUI applications):
```shell
pyinstaller --onefile --noconsole FastbootGuiMini.py
```

- Add an icon to the executable:
```shell
pyinstaller --onefile --icon=icon.ico FastbootGuiMini.py
```

### "PS: In the Release section, you will find 3 different GUI versions with precompiled downloads via PyInstaller for Linux, along with detailed information about each Project GUI available."



