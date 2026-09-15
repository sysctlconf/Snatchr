@echo off
REM Builds Snatchr.exe - a single-file, double-clickable app with the custom icon baked in.
REM Run this from the Snatchr folder after: pip install -r requirements.txt

pyinstaller --noconfirm --onefile --windowed ^
  --name "Snatchr" ^
  --icon "assets\icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "core;core" ^
  app.py

echo.
echo Done. Find Snatchr.exe in the dist\ folder.
pause
