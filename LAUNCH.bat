@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "UVICORN=%PROJECT_ROOT%\.venv\Scripts\uvicorn.exe"
set "APP_URL=http://127.0.0.1:8000/"

if not exist "%UVICORN%" (
    echo The project virtual environment was not found.
    echo Run .\.tools\uv\uv.exe sync --extra test --python .\.venv\Scripts\python.exe from the project root first.
    exit /b 1
)

echo Starting Docs to Markdown at %APP_URL%
start "" "%APP_URL%"
call "%UVICORN%" docs_to_markdown.api:app --app-dir "%PROJECT_ROOT%\src" --host 127.0.0.1 --port 8000