@echo off
setlocal
cd /d "%~dp0"

REM ==============================================================
REM Dashboard FGTS - inicializador Windows sem privilegio de admin
REM Correção: o ambiente virtual fica em %%LOCALAPPDATA%% para evitar
REM erro de caminho longo do Windows/OneDrive durante instalacao.
REM ==============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python ou adicione ao PATH.
    pause
    exit /b 1
)

set "VENV_DIR=%LOCALAPPDATA%\fgts_dashboard_venv"

echo.
echo Usando ambiente virtual em:
echo %VENV_DIR%
echo.

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Criando ambiente virtual local fora do OneDrive...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo Atualizando pip e instalando dependencias...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt

if errorlevel 1 (
    echo.
    echo Erro ao instalar dependencias.
    echo Dica: mova a pasta do dashboard para um caminho curto, por exemplo:
    echo C:\FGTS_DASH
    echo ou C:\Users\%USERNAME%\FGTS_DASH
    echo Depois apague a pasta %VENV_DIR% e execute novamente.
    pause
    exit /b 1
)

echo.
echo Abrindo Dashboard FGTS...
echo O navegador sera aberto automaticamente em alguns segundos.
REM Streamlit fica em modo headless para evitar abrir duas abas.

set "DASH_URL=http://localhost:8501"
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process '%DASH_URL%'"

"%VENV_DIR%\Scripts\python.exe" -m streamlit run app.py --server.address localhost --server.port 8501 --server.headless true

pause
