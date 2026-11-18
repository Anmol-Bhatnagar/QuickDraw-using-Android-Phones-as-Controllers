@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0.venv\Lib\site-packages
echo Starting Game Console Server...
"C:\Users\anmol\AppData\Local\Programs\Python\Python313\python.exe" console_server.py %*
pause
