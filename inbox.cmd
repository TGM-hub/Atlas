@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem Range les images de _inbox\ dans images\ puis relance le build. Options : --dry-run, --yes, --no-build
rem "python" peut etre le raccourci du Microsoft Store : on essaie py d'abord
py -c "import PIL" >nul 2>nul && (py tools\inbox.py %*) || (python tools\inbox.py %*)
pause
