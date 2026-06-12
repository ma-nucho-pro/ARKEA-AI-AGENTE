@echo off
chcp 65001 >nul
title Crear EXE ARKEA AI
cd /d "%~dp0"
echo =====================================
echo ARKEA AI - crear instalador .EXE
echo by: Arkeai AI Roberto Manuel Jara Peche
echo =====================================
echo.
if not exist "build_windows_installer.ps1" (
  echo ERROR: No estoy en la carpeta correcta. Debe existir build_windows_installer.ps1
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_installer.ps1"
echo.
echo Si la compilacion termino bien, revisa la carpeta release.
explorer "%~dp0release"
pause
