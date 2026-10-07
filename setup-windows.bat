@echo off
cd /d "%~dp0"
echo Please use Python 3.11 for this project.
python --version
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Ready. Double-click start-game.bat to play.
pause
exit /b 0
:failed
echo.
echo Setup failed. Check your Python version and internet connection.
pause
exit /b 1
