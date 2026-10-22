@echo off
rem ============================================================
rem  "actualizacion definitive.bat" - EL BOTON UNICO de este sitio.
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set PY=py
where py >nul 2>nul || set PY=python

set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

%PY% actualizador.py %PASO_FINAL%

echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
