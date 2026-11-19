@echo off
title Telegram Session String Generator
cd /d "%~dp0"
echo ====================================================
echo Starting Telegram Session Generator...
echo ====================================================
python scripts\telegram\generate_session.py
echo.
echo ====================================================
echo Press any key to close this window...
echo ====================================================
pause >nul
