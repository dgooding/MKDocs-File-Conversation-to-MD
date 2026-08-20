$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-Python312 {
    $commands = Get-Command py, python -ErrorAction SilentlyContinue
    foreach ($command in $commands) {
        try {
            $version = & $command.Source --version 2>&1
            if ($version -match "Python 3\.12\.") {
                return $command.Source
            }
        } catch {
            continue
        }
    }
    return $null
}

function Install-WithWinget([string]$packageId, [string]$displayName) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is required to install $displayName automatically. Install it from the Microsoft Store, then run this script again."
    }

    Write-Host "Installing $displayName..."
    & winget install --id $packageId --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget could not install $displayName. Install it manually, then run this script again."
    }
}

$python = Get-Python312
if (-not $python) {
    Install-WithWinget "Python.Python.3.12" "Python 3.12"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Install-WithWinget "astral-sh.uv" "uv"
}

$launcher = Join-Path $projectRoot "LAUNCH.bat"
if (-not (Test-Path $launcher)) {
    throw "LAUNCH.bat was not found in $projectRoot."
}

Write-Host "Starting Docs to Markdown..."
& $launcher