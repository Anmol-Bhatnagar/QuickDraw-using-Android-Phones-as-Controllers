@echo off
:: Batch script to allow Quickdraw Game Console through Windows Firewall
netsh advfirewall firewall add rule name="Quickdraw Game Console Ports" dir=in action=allow protocol=TCP localport=8000,8080,8443 enable=yes
if %errorlevel% equ 0 (
    echo.
    echo ==============================================================
    echo [SUCCESS] Windows Firewall rule added successfully!
    echo Ports 8000, 8080, and 8443 are now open for your phone on Wi-Fi.
    echo ==============================================================
) else (
    echo.
    echo ==============================================================
    echo [NOTE] Right-click setup_firewall.bat and choose "Run as administrator"
    echo to allow incoming connections from your phone.
    echo ==============================================================
)
pause
