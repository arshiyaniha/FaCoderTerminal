@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3 -m venv .venv
)
echo Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo Starting Simple Persian PowerShell...
".venv\Scripts\python.exe" -m simple_terminal.main
