@echo off
REM Veckovis djupanalys med e-post
REM Körs automatiskt via Windows Task Scheduler (fredagar)

cd /d C:\Users\josef\claude-smallcap-se

echo [%date% %time%] Startar veckovis djupanalys...
python -m app.main weekly --email

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Veckoanalys skickad!
) else (
    echo [%date% %time%] FEL: Kunde inte skicka veckoanalys (kod %ERRORLEVEL%)
)

echo [%date% %time%] Klar.
