----------------------------------
**_You have a choice of 3 GUI interfaces, with descriptions available in the releases._**
----------------------------------

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

**_How Install PyInstaller ?_**
1. Download Python

Go to the official website: https://www.python.org/downloads/

Click on Download Python 3.x.x (choose the latest stable version).


2. Start the Installation

Open the python-3.x.x.exe installer you just downloaded.

Check the "Add Python to PATH" box (very important, or Windows won’t know where to find it).

Click Install Now.


3. Verify the Installation

Once installed, open the command prompt (Win + R → type cmd → Enter) and type:

python --version

or

python3 --version

If it returns a version number (Python 3.x.x), you're good to go!

4. Test in a Terminal

Still in the console, just type:

python

You should see the Python interpreter start (>>>).

**_Pip Not Working ?_**
Pip is usually installed with Python, but if it's missing or broken, here’s how to (re)install it properly on Windows.


---

1. Check if pip is already installed

Open Command Prompt (Win + R → type cmd → Enter) and run:

pip --version

If you see something like:

pip 23.0.1 from C:\Users\YourName\AppData\Local\Programs\Python\Python3x\lib\site-packages\pip (python 3.x)

Then pip is already installed! (If not, keep going 👇)


---

2. Manually install pip

Method 1: Using ensurepip (if Python ≥ 3.4)

In Command Prompt, run:

python -m ensurepip --default-pip

Then check with:

pip --version

Method 2: Using get-pip.py (if ensurepip doesn’t work)

1. Download get-pip.py from this official link.


2. Save the file in your Downloads folder (or anywhere you’ll remember).


3. Open Command Prompt and navigate to the folder, e.g.:

cd %USERPROFILE%\Downloads


4. Then run:

python get-pip.py


5. Once done, check with:

pip --version




---

3. Add pip to the PATH variable (if needed)

If pip still doesn’t work, Windows might not know where to find it. Try:

python -m pip --version

If that works, you need to add its path to the PATH variable.

1. Search for "Environment Variables" in the Start menu.


2. Edit the Path variable and add:

C:\Users\YourName\AppData\Local\Programs\Python\Python3x\Scripts\


3. Restart your terminal and try pip --version again.




---

4. Test pip installation

To check if pip is working properly, install a simple package like requests:

pip install requests

Then test it in Python:

import requests
print(requests.__version__)

If it works, congrats, pip is installed! 🎉



