@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ARKEA AI OmniAgent - Subir codigo a GitHub

set "REPOSITORY=https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE.git"
set "STAGING=%TEMP%\arkea-github-upload-%RANDOM%-%RANDOM%"
set "SOURCE=%~dp0"
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git no esta instalado.
  pause
  exit /b 1
)
where gh >nul 2>nul
if errorlevel 1 (
  echo ERROR: GitHub CLI no esta instalado.
  echo Descarga el MSI oficial desde: https://cli.github.com/
  echo Instalalo y abre una consola nueva.
  pause
  exit /b 1
)

gh auth status >nul 2>nul
if errorlevel 1 (
  echo ERROR: Primero ejecuta: gh auth login
  pause
  exit /b 1
)

echo ============================================================
echo  REEMPLAZAR CODIGO DE GITHUB
echo ============================================================
echo Repositorio: %REPOSITORY%
echo Rama: main
echo.
echo Se reemplazaran los archivos visibles actuales por este proyecto nuevo.
echo El historial anterior se conservara para poder recuperarlo.
echo Los issues y Releases anteriores no se borraran.
echo La carpeta local release no se enviara al repositorio.
echo.
choice /C SN /M "Deseas continuar"
if errorlevel 2 exit /b 0

gh auth setup-git
if errorlevel 1 goto :error

git clone --branch main --single-branch "%REPOSITORY%" "%STAGING%"
if errorlevel 1 goto :error

git -C "%STAGING%" rm -r .
if errorlevel 1 goto :error

robocopy "%SOURCE%" "%STAGING%" /E /R:2 /W:1 /XD ".git" "release" "_work" "node_modules" ".venv" "venv" "__pycache__" ".pytest_cache" /XF "*.db" "*.sqlite" "*.sqlite3" "runtime-secrets.bin" "runtime-secrets.json" /NFL /NDL /NP
set "ROBOCOPY_RESULT=%ERRORLEVEL%"
if %ROBOCOPY_RESULT% GEQ 8 (
  echo ERROR: no se pudo copiar el proyecto. Codigo de robocopy: %ROBOCOPY_RESULT%
  goto :error
)

git -C "%STAGING%" config user.name "ma-nucho-pro"
git -C "%STAGING%" config user.email "275824378+ma-nucho-pro@users.noreply.github.com"
git -C "%STAGING%" add -A

echo.
echo Cambios que se publicaran:
git -C "%STAGING%" status --short
echo.
choice /C SN /M "Confirmas el commit y push a main"
if errorlevel 2 goto :cancel

git -C "%STAGING%" commit -m "Publicar ARKEA AI OmniAgent 0.1"
if errorlevel 1 goto :error
git -C "%STAGING%" push origin main
if errorlevel 1 goto :error

rmdir /S /Q "%STAGING%"
echo.
echo CODIGO PUBLICADO CORRECTAMENTE.
echo https://github.com/ma-nucho-pro/ARKEA-AI-AGENTE
pause
exit /b 0

:cancel
rmdir /S /Q "%STAGING%"
echo Publicacion cancelada.
pause
exit /b 0

:error
echo.
echo ERROR: no se completo la publicacion.
echo La carpeta temporal se conserva para diagnostico:
echo %STAGING%
pause
exit /b 1
