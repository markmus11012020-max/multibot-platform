@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM ============================================================
REM   start.bat — автодеплой мультибот-платформы (Windows)
REM   Шаги:
REM     1) остановить старые процессы streamlit
REM     2) очистить кэши Python
REM     3) создать/обновить .venv
REM     4) установить зависимости
REM     5) подготовить .env из .env.example (если ��ет)
REM     6) запустить приложение
REM ============================================================

cd /d "%~dp0"

echo [1/6] Stop old Streamlit processes...
taskkill /F /IM streamlit.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq streamlit*" 2>nul

echo [2/6] Clear Python caches...
for /d /r "src" %%d in (__pycache__) do @rd /s /q "%%d" 2>nul
for /d /r "src" %%d in (.pytest_cache) do @rd /s /q "%%d" 2>nul
for /d /r "src" %%d in (.mypy_cache) do @rd /s /q "%%d" 2>nul
del /s /q "%~dp0src\*.pyc" 2>nul

echo [3/6] Create virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Check Python installation.
        exit /b 1
    )
)

echo [4/6] Install dependencies...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

echo [5/6] Prepare .env from template...
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo .env created from .env.example. Open it and set AITUNNEL_API_KEY.
    ) else (
        echo [WARN] .env.example not found, skipping.
    )
) else (
    echo .env already exists, keeping it.
)

echo [6/6] Launch Streamlit...
echo.
echo   Open http://localhost:8501 in your browser.
echo.
streamlit run app.py

endlocal
