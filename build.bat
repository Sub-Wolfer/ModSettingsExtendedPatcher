@echo off
rem Builds dist\ModSettingsExtendedPatcher.exe (Windows, Python 3.10+).
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --noconfirm --onefile --windowed --name ModSettingsExtendedPatcher --paths src src\mse_patcher.py
