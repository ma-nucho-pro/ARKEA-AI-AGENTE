@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo ARKEA AI - SUBIR PROYECTO COMPLETO A GITHUB
echo by: Arkeai AI Roberto Manuel Jara Peche
echo ============================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git no esta instalado o no esta en PATH.
  pause
  exit /b 1
)

set /p REPO_URL=Pegue la URL HTTPS del repositorio, por ejemplo https://github.com/usuario/arkea-ai.git: 
if "%REPO_URL%"=="" (
  echo ERROR: Debe indicar la URL del repositorio.
  pause
  exit /b 1
)

if not exist ".git" git init
git branch -M main
git add .
git commit -m "Publicar proyecto completo ARKEA AI"

git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin "%REPO_URL%"
) else (
  git remote set-url origin "%REPO_URL%"
)

git push -u origin main
if errorlevel 1 (
  echo.
  echo No se pudo completar el push. Revise el inicio de sesion de GitHub y la URL.
  pause
  exit /b 1
)

echo.
echo Proyecto enviado correctamente a GitHub.
pause
