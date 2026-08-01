@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title ARKEA AI OmniAgent 0.1 - Crear instalador

if not exist "build_windows_installer.ps1" (
  echo ERROR: No se encontro build_windows_installer.ps1.
  echo Ejecuta este archivo desde la raiz del repositorio.
  pause
  exit /b 1
)

echo ============================================================
echo  ARKEA AI OmniAgent - construir instalador Windows
echo ============================================================
echo Requisitos para compilar: Windows, Git, Python 3.11 y Node 22.
echo El proceso descarga dependencias verificadas y puede tardar.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_installer.ps1"
set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" (
  echo La compilacion termino con error %EXITCODE%.
) else (
  echo Compilacion completada. Los archivos estan en release.
)
pause
exit /b %EXITCODE%
