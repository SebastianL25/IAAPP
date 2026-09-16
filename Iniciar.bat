@echo off
title xSlou Clips AI
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno instalado.
    echo Ejecuta primero "Instalar.bat" ^(doble clic^).
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [ERROR] La interfaz web aun no esta compilada.
    echo Ejecuta primero "Instalar.bat" ^(doble clic^).
    pause
    exit /b 1
)

echo Iniciando xSlou Clips AI...
echo No cierres esta ventana mientras uses la app. Ciérrala para detener el programa.
echo.

start /b "" backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8756 --app-dir backend

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8756

echo.
echo La aplicacion esta corriendo en http://127.0.0.1:8756
echo Deja esta ventana abierta. Cierrala cuando termines de usar la app.
echo.
pause >nul
