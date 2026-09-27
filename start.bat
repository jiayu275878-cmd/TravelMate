@echo off
title TravelMate

echo ==============================
echo       TravelMate launcher
echo ==============================
echo.

start "TravelMate Backend" cmd /k "chcp 65001 >nul && cd /d D:\Projects\TravelMate\backend && .venv\Scripts\python.exe app.py"
start "TravelMate Frontend" cmd /k "chcp 65001 >nul && cd /d D:\Projects\TravelMate\frontend && npm.cmd run dev"

echo Waiting 10 seconds for both servers to start...
timeout /t 10 >nul

start http://localhost:5173/

echo.
echo Frontend app   : http://localhost:5173/
echo Map key check  : http://localhost:5173/key-check.html
echo Backend health : http://127.0.0.1:5000/api/health
echo.
echo Before opening the page, check the frontend window for this line:
echo     Local:   http://localhost:5173/
echo.
pause
