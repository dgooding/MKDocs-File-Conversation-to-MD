@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "UVICORN=%PROJECT_ROOT%\.venv\Scripts\uvicorn.exe"
set "APP_URL=http://127.0.0.1:8000/"

where uv >nul 2>&1
if errorlevel 1 (
    echo Could not find "uv" on your PATH.
    echo Install uv from https://docs.astral.sh/uv/getting-started/installation/
    echo Then run this launcher again. The launcher installs the Python dependencies after uv is available.
    exit /b 1
)

echo Installing or updating all locked project dependencies.
pushd "%PROJECT_ROOT%"
uv sync --locked --all-extras --system-certs
if errorlevel 1 (
    popd
    echo Dependency setup failed while running the locked sync.
    echo If your network uses TLS inspection, confirm uv can use the system certificate store.
    exit /b 1
)
popd

if not exist "%UVICORN%" (
    echo Setup completed but Uvicorn was not found at:
    echo %UVICORN%
    exit /b 1
)

echo Starting Docs to Markdown at %APP_URL%
start "" "%APP_URL%"
call "%UVICORN%" docs_to_markdown.api:app --app-dir "%PROJECT_ROOT%\src" --host 127.0.0.1 --port 8000