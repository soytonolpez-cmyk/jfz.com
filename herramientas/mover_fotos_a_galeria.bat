@echo off
rem ============================================================
rem  "mover_fotos_a_galeria.bat" - Mueve tus fotos a fotos\galeria
rem  (la carpeta que lee la galeria del sitio) y regenera la galeria.
rem  Doble clic. Si quieres ver primero QUE haria sin mover nada,
rem  abre una consola y ejecuta:
rem     py herramientas\mover_fotos_a_galeria.py --solo-ver
rem ============================================================
chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
set PY=py
where py >nul 2>nul || set PY=python
%PY% herramientas\mover_fotos_a_galeria.py %*
echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
