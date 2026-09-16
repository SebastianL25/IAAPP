@echo off
setlocal enabledelayedexpansion
title xSlou Clips AI - Instalacion
cd /d "%~dp0"

echo ==================================================
echo   xSlou Clips AI - Instalacion (no requiere admin)
echo ==================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] No se encontro Python instalado.
        echo Descarga Python 3.10 o superior desde https://www.python.org/downloads/
        echo Durante la instalacion marca la casilla "Add Python to PATH".
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Node.js instalado.
    echo Descarga la version LTS desde https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Creando entorno virtual de Python en backend\.venv ...
if not exist "backend\.venv" (
    %PYTHON_CMD% -m venv backend\.venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

echo [2/4] Instalando dependencias de Python (puede tardar varios minutos)...
call backend\.venv\Scripts\python.exe -m pip install --upgrade pip
call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias de Python.
    pause
    exit /b 1
)

echo [3/4] Instalando dependencias del frontend...
pushd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Fallo "npm install".
    popd
    pause
    exit /b 1
)

echo [4/4] Compilando la interfaz web...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la compilacion del frontend.
    popd
    pause
    exit /b 1
)
popd

echo.
echo ==================================================
echo   Instalacion completada.
echo   Ahora puedes usar "Iniciar.bat" para abrir la app.
echo ==================================================
echo.
echo NOTA: FFmpeg no se instala automaticamente. Si "Iniciar.bat"
echo indica que no lo encuentra, descarga una build de FFmpeg para
echo Windows (por ejemplo desde https://www.gyan.dev/ffmpeg/builds/),
echo descomprimela, y configura la ruta absoluta de ffmpeg.exe dentro
echo de la app, en el panel de Ajustes.
echo.
pause
