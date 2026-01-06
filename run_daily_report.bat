@echo off
REM Daglig aktie-rapport med e-post
REM Körs automatiskt via Windows Task Scheduler

cd /d C:\Users\josef\claude-smallcap-se

REM Aktivera rätt Python-miljö om behövs
REM call venv\Scripts\activate.bat

echo [%date% %time%] Startar daglig aktie-rapport...
python -m app.main smart --email

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Rapport skickad!
) else (
    echo [%date% %time%] FEL: Kunde inte skicka rapport (kod %ERRORLEVEL%)
)

echo [%date% %time%] Klar.
