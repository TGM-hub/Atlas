@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem Liens sortants (trainers, Plonk It, LearnableMeta) : lent et mis en cache 7 jours
py tools\check_links.py %* || python tools\check_links.py %*
pause
