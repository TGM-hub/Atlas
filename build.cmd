@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem "python" peut etre le raccourci du Microsoft Store : on essaie py d'abord
py -c "import PIL" >nul 2>nul && (py build.py) || (python build.py)
pause
