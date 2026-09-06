@echo off
setlocal

cd /d "%~dp0"

if "%PYTHON%"=="" set "PYTHON=python"
if "%HOLOLIVE_MAX_VIDEOS%"=="" set "HOLOLIVE_MAX_VIDEOS=0"

echo [1/4] Generating Haraki Hibiya JSON...
"%PYTHON%" scripts\generate_haraki_hibiya.py
if errorlevel 1 goto failed

echo [2/4] Generating Hololive JP JSON...
if "%YOUTUBE_API_KEY%"=="" (
    echo YOUTUBE_API_KEY is not set. Generating Hololive JP PERSON and EXPERIENCE only.
    "%PYTHON%" scripts\generate_hololive_jp.py
) else (
    if "%HOLOLIVE_INCLUDE_DEV_IS%"=="1" (
        "%PYTHON%" scripts\generate_hololive_jp.py --max-videos %HOLOLIVE_MAX_VIDEOS% --include-dev-is
    ) else (
        "%PYTHON%" scripts\generate_hololive_jp.py --max-videos %HOLOLIVE_MAX_VIDEOS%
    )
)
if errorlevel 1 goto failed

echo [3/4] Validating HASM JSON...
"%PYTHON%" scripts\validate_hasm_examples.py
if errorlevel 1 goto failed

echo [4/4] Generating HASM output folders...
"%PYTHON%" scripts\generate_hasm_folder.py --output output --force
if errorlevel 1 goto failed

echo Done.
exit /b 0

:failed
echo Failed. See the error output above.
exit /b 1