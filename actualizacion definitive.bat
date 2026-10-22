@echo off
rem ============================================================
rem  "actualizacion definitive.bat" - EL BOTON UNICO de este sitio.
rem  Vive en la RAIZ del proyecto (junto a las fotos y las paginas).
rem  Doble clic y hace TODO el flujo automatico de una sola vez:
rem    python actualizador.py  ->  ordena fotos\, aplica los parches
rem    del sitio, convierte por-procesar\ a WebP con marca de agua,
rem    deja fotos\galeria\ como ESPEJO EXACTO de por-procesar\
rem    (los mismos numeros, nombres y cantidad de archivos .webp)
rem    y regenera assets\js\fotos.js
rem  Despues: GitHub Desktop -> Commit to main -> Push origin.
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizacion definitive.bat" 1  -> solo orden + parches
rem    "actualizacion definitive.bat" 2  -> hasta convertir/espejar fotos
rem    "actualizacion definitive.bat" 3  -> todo el flujo (por defecto)
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem --- elige el interprete de Python (py = el lanzador de Windows; si no, python) ---
set PY=py
where py >nul 2>nul || set PY=python

rem --- paso final por defecto: 3 = todo el flujo; acepta un numero como argumento ---
set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

%PY% actualizador.py %PASO_FINAL%

echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
