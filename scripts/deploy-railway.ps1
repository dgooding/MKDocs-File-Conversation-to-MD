# Deploy this app to Railway (public URL + full Docker deps).
# Run in PowerShell from the project root:
#   .\scripts\deploy-railway.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Checking Railway CLI..." -ForegroundColor Cyan
if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host "Railway CLI not found. Installing via winget..." -ForegroundColor Yellow
    winget install -e --id Railway.Railway --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host @"

Could not find railway after install. Install manually:
  https://docs.railway.com/guides/cli
Then re-run this script.

"@ -ForegroundColor Red
    exit 1
}

Write-Host "==> Logging in (browser will open)..." -ForegroundColor Cyan
railway login

Write-Host "==> Deploying Docker service..." -ForegroundColor Cyan
railway up -y

Write-Host "==> Creating public domain..." -ForegroundColor Cyan
railway domain

Write-Host @"

Done. Open the URL Railway printed, then go to /convert/

Health:  https://YOUR-HOST/api/health
Engines: https://YOUR-HOST/api/engines

"@ -ForegroundColor Green
