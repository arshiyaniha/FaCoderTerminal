$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    py -3 -m venv .venv
}

Write-Host "Installing requirements..." -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller

Write-Host "Building executable..." -ForegroundColor Cyan
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name SimplePersianPowerShell `
    --add-data "simple_terminal\web;simple_terminal\web" `
    --hidden-import simple_terminal.simple_api `
    --hidden-import simple_terminal.simple_pty `
    simple_terminal\main.py

$Exe = Join-Path $Root "dist\SimplePersianPowerShell.exe"
if (Test-Path $Exe) {
    Write-Host "Build completed:" -ForegroundColor Green
    Write-Host $Exe -ForegroundColor Yellow
} else {
    throw "Build failed. Executable was not created."
}
