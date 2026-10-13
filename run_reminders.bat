@echo off
REM Runs the daily Hifaya reminders (in-app + e-mail) and writes a log you can read.
REM Task Scheduler should run THIS file (keep it in the same folder as manage.py).
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%date% %time%] Starting reminders >> logs\reminders.log
call venv\Scripts\activate.bat
python manage.py send_reminders >> logs\reminders.log 2>&1
echo [%date% %time%] Finished (exit code %errorlevel%) >> logs\reminders.log
