@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0.venv\Lib\site-packages

echo ==================================================
echo   PHONE-CONTROLLER GAME LIBRARY - STARTING...
echo ==================================================
echo.
echo Starting server + ngrok tunnel...
echo (Ngrok creates a public URL that bypasses firewalls)
echo.
echo Once started, scan the QR code or use the URL shown
echo below to connect your phone from ANY network.
echo.
echo Press Ctrl+C to stop the server.
echo ==================================================

"C:\Users\anmol\AppData\Local\Programs\Python\Python313\python.exe" console_server.py %*
pause
