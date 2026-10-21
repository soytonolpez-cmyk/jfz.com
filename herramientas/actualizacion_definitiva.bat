@echo off
rem ============================================================
rem  "actualizacion_definitiva.bat" - EL BOTON UNICO de este sitio.
rem  Doble clic y hace TODO el flujo automatico, en orden:
rem    1) actualizacion_definitiva.py  (mueve las fotos sueltas que queden
rem       dentro de fotos\ en la carpeta general fotos\galeria, jubila las
rem       secciones Legado/Prueba Trimestre, aplica los parches del sitio
rem       y consolida los botones)
rem    2) preparar_fotos.py            (fotos de por-procesar\ -> WebP con
rem       marca de agua en fotos\galeria; usa herramientas\marca_agua.png)
rem    3) actualizar_galeria.py        (regenera assets/js/fotos.js)
rem  Despues: GitHub Desktop -> Commit to main -> Push origin.
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizacion_definitiva.bat" 1  -> solo jubilacion + parches
rem    "actualizacion_definitiva.bat" 2  -> hasta convertir fotos
rem    "actualizacion_definitiva.bat" 3  -> todo el flujo (por defecto)
rem  Para DEVOLVER Legado/Prueba Trimestre a la galeria:
rem    py herramientas\actualizacion_definitiva.py --revertir
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

rem --- elige el interprete de Python (py = el lanzador de Windows; si no, python) ---
set PY=py
where py >nul 2>nul || set PY=python

rem --- paso final por defecto: 3 = todo el flujo; acepta un numero como argumento ---
set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

echo === 1^) Actualizacion definitiva: ordenar fotos + jubilar Legado/Prueba + parches ===
%PY% herramientas\actualizacion_definitiva.py
if errorlevel 1 (echo Hubo un problema en la actualizacion. Avsale a Claude. & goto fin)
if %PASO_FINAL% LSS 2 goto fin
echo.

echo === 2^) Convirtiendo fotos nuevas a WebP (con marca de agua) ===
%PY% herramientas\preparar_fotos.py
if errorlevel 2 (echo Hubo un problema al convertir. Avsale a Claude. & goto fin)
if errorlevel 1 echo   ^(no habia fotos nuevas en por-procesar: continuo con la galeria^)
if %PASO_FINAL% LSS 3 goto fin
echo.

echo === 3^) Actualizando la galeria ===
%PY% herramientas\actualizar_galeria.py

:fin
echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
