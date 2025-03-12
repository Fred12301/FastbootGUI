Sharing Multiple Versions of the GUI Interface.

Each version has different features but retains the main functionality of flashing a partition via Fastboot.

-----------------------------------
Window : 
To compile a Python script into an executable (.exe) on Windows, you can use PyInstaller. Here are the detailed steps:

1. Install PyInstaller

Open a command prompt (CMD) and type:

pip install pyinstaller

2. Compile the script into an executable

Navigate to the folder where your Python script is located (e.g., script.py) using the cd command, then run:

pyinstaller --onefile script.py

This will generate an .exe file in the dist/ folder.

3. Useful options with PyInstaller

Create an executable without a console (for GUI applications):

pyinstaller --onefile --noconsole script.py

Add an icon to the executable:

pyinstaller --onefile --icon=icon.ico script.py


4. Retrieve the executable

The executable is located in the dist/ folder. You can copy and run it on other machines without needing to install Python.

