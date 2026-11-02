@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt "pyinstaller>=6,<7"
if errorlevel 1 goto error
pyinstaller --noconfirm --clean --onefile --windowed --name EdgeReader-2.0 --collect-all edge_tts --collect-all miniaudio edge_reader.py
if errorlevel 1 goto error
echo.
echo Created: dist\EdgeReader-2.0.exe
pause
exit /b 0
:error
echo Build failed. Check the messages above.
pause
exit /b 1
