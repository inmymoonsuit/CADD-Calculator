@echo off
rem Launch the work-in-progress desktop app from this checkout (docs\dev\launching.md).
rem Usage: scripts\launch_app.cmd [--branding FOLDER] [app arguments]
setlocal
set "PROJECT_ROOT=%~dp0.."

where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found. Install it from https://docs.astral.sh/uv/ and try again.
    pause
    exit /b 1
)

uv run --project "%PROJECT_ROOT%" --extra gui python "%PROJECT_ROOT%\scripts\launch_app.py" %*
set "STATUS=%errorlevel%"
if not "%STATUS%"=="0" (
    echo.
    echo CADD Calculator exited with status %STATUS%.
    pause
)
exit /b %STATUS%
