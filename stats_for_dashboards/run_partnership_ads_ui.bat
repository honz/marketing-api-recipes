@echo off
REM Partnership Ads UI Wrapper Script for Windows
REM This script sets up the environment and runs the Partnership Ads UI

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%venv

cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists, if not create it
if not exist "%VENV_DIR%" (
    echo 🔧 Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM Install/upgrade dependencies
echo 📦 Installing dependencies...
pip install --quiet --upgrade requests streamlit pandas

REM Run the Streamlit app
echo 🚀 Starting Partnership Ads UI...
echo    Access the UI at: http://localhost:8501
echo.
streamlit run partnership_ads_ui.py %*
