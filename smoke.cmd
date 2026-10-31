@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem Tests de fumee de l Atlas et des trainers (Edge sans fenetre). Premiere fois : py -m pip install playwright
where py >nul 2>nul
if %errorlevel%==0 (py tools\smoke.py %*) else (python tools\smoke.py %*)
pause
