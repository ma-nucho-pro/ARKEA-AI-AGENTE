@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title ARKEA AI OmniAgent - Publicar GitHub Release

set "TAG=%~1"
if "%TAG%"=="" set "TAG=v0.1.0"

where gh >nul 2>nul
if errorlevel 1 (
  echo ERROR: Falta GitHub CLI ^(gh^).
  echo Descarga el MSI oficial desde: https://cli.github.com/
  echo Instalalo, abre una consola nueva y ejecuta: gh auth login
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\publicar_release_github.ps1" -Tag "%TAG%"
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" echo Release %TAG% publicada correctamente.
if not "%EXITCODE%"=="0" echo No se pudo publicar la Release %TAG%.
pause
exit /b %EXITCODE%
