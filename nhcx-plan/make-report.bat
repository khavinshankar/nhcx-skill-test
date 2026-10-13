@echo off
rem nhcx-plan\make-report.bat: rebuild report.html every 10 seconds until stopped (Ctrl-C).
rem "make-report.bat once" rebuilds it one time.
cd /d "%~dp0"
if "%1"=="once" ( python report.py & exit /b %errorlevel% )
:loop
python report.py && echo %time% report.html rebuilt || echo %time% report build failed
timeout /t 10 /nobreak >nul
goto loop
