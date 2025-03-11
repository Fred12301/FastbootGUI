# FastbootGUI

Complete Description of FastBootGUI


---

1. Introduction

FastBootGUI is a graphical application developed with Kivy for managing ADB (Android Debug Bridge) and Fastboot, two essential tools for administering Android devices via USB.

The application provides a user-friendly interface that allows users to:

Install and update ADB/Fastboot

Execute Fastboot and ADB commands

Flash partitions on an Android device

Display system information via Fastboot

Interact with connected Android devices


It is designed to work on both Windows and Linux, handling background operations through multi-threading to ensure the interface remains responsive while commands are being executed.


---

2. Key Features

Installation and Update of ADB/Fastboot

The application enables users to:

Check if ADB and Fastboot are installed (Check ADB/Fastboot).

Download and install the latest version of Google’s platform-tools.

Update ADB/Fastboot if an outdated version is detected.


Optimizations:

Resumable download in case of interruptions.

Integrity verification using a hash check on the downloaded file.

Automatic extraction of the archive after downloading.



---

Android Device Management

FastBootGUI provides the following functionalities:

List connected ADB devices (Check ADB Devices).

List connected Fastboot devices (Check Fastboot Devices).

Check if a device is in FastbootD mode.

Display all Fastboot variables (getvar all).

Reboot devices into various modes:

Recovery Mode (Reboot Recovery).

Bootloader/Fastboot Mode (Reboot Bootloader).

FastbootD Mode (Reboot FastbootD).

EDL (Emergency Download Mode) (Reboot EDL).




---

Advanced Flashing Management

The application allows users to flash a firmware or file onto a specific partition:

Select a .img, .tar, or .zip file (Browse).

Choose the target partition (system, boot, recovery, vendor, etc.).

Select the target slot (A, B, or None for global partitions).

Verify device status before flashing.

Enable verbose mode to display detailed logs.

Enable force mode to bypass warnings.


Before flashing, a confirmation dialog box appears to prevent accidental actions.


---

Sideload Command

The application supports sideloading to install system updates without a PC:

Select a .zip file to be flashed.

Choose between adb -b sideload or adb -a sideload modes.



---

Additional Tools

Erase the cache via Fastboot (Erase Cache).

View connected USB devices (Check LSUSB – Linux only).

Export logs to a .txt file.

Cancel ongoing operations (e.g., downloading) via the Cancel Operation button.



---

3. Technology Used

Graphical Interface

The user interface is built with Kivy, a Python library for developing modern and responsive applications.

Multi-threading Management

Long-running operations (downloads, flashing, sideloading) run in separate threads to keep the user interface responsive.

Logging and Debugging

Logs are displayed directly in the graphical interface.

A adbinstaller.log file stores a complete history of operations.

Users can dynamically change the logging level (DEBUG, INFO, WARNING, ERROR).



---

4. Options and Settings

Customizable Configuration

The application allows users to customize several settings:

Logging level (DEBUG, INFO, WARNING, ERROR).

Enable "Force Install" mode to bypass restrictions.

Enable verbose logging to display more detailed logs.


Security and Confirmation

Automatic privilege verification (admin/root) before executing critical commands.

Confirmation dialogs before performing critical actions (flashing, rebooting into EDL mode).



---

5. Improvements and Optimizations

This script includes several advanced optimizations:

Enhanced error handling: If a Fastboot command fails, an error message is displayed with troubleshooting tips.

Resumable downloads: If a file is partially downloaded, the script resumes from the last received byte.

Validation of downloaded files using hash verification (SHA256).

Automatic removal of old versions when updating.

Addition of a cancel button to stop an ongoing download.

Progress bar for downloads and extraction processes.



---

6. Use Cases

FastBootGUI is ideal for:

Android developers who regularly flash firmwares and custom ROMs.

Repair technicians who need quick access to ADB and Fastboot tools.

Advanced users who want to modify their device (custom recovery installation, rooting, etc.).

System partition backup and recovery before making critical changes.



---

7. Conclusion

FastBootGUI is a complete and robust solution for managing Fastboot and ADB with an intuitive graphical interface. With its numerous features, modular architecture, and advanced optimizations, it simplifies complex tasks related to Android device management.

by Grondines
