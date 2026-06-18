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

Write-Host "Cleaning old build output..." -ForegroundColor Cyan
$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"
$SpecFile = Join-Path $Root "SimplePersianPowerShell.spec"
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
if (Test-Path $SpecFile) { Remove-Item $SpecFile -Force }

Write-Host "Building executable folder with PyInstaller --onedir..." -ForegroundColor Cyan
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name SimplePersianPowerShell `
    --add-data "simple_terminal\web;simple_terminal\web" `
    --hidden-import simple_terminal.simple_api `
    --hidden-import simple_terminal.simple_pty `
    simple_terminal\main.py

$Exe = Join-Path $Root "dist\SimplePersianPowerShell\SimplePersianPowerShell.exe"
if (Test-Path $Exe) {
    Write-Host "Build completed:" -ForegroundColor Green
    Write-Host $Exe -ForegroundColor Yellow
    Write-Host "Important: run the exe from inside this folder. Do not move only the exe file; keep the whole SimplePersianPowerShell folder together." -ForegroundColor Yellow
} else {
    throw "Build failed. Executable was not created."
}
