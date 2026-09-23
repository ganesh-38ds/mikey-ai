@echo off
echo.
echo  ====================================
echo   Mikey Server Starting...
echo  ====================================
echo.
echo  Starting local server...
echo  Starting secure mobile tunnel...

start cmd /k "echo Starting Secure Mobile Tunnel... && echo Please wait for the HTTPS URL to appear below. && echo. && npx localtunnel --port 8000"

echo.
echo  [LAPTOP]: Open http://localhost:8000 in your browser.
echo  [MOBILE]: Check the new command window that just opened, copy the HTTPS link, and open it on your phone!
echo.
echo  Press Ctrl+C to stop the local server.
echo.

IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --timeout-keep-alive 75
) ELSE (
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --timeout-keep-alive 75
)
pause
