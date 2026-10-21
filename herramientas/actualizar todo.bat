@echo off
rem ============================================================
rem  "actualizar todo.bat" - EL BOTON UNICO de este sitio.
rem  Doble clic y hace TODO el flujo automatico, en orden:
rem    0) consolidar_sitio.py    (repara/agrega los botones del sitio)
rem    1) parche_webp.py         (el sitio reconoce fotos .webp)
rem    2) parche_galeria.py      (conecta el mosaico mejorado)
rem    3) preparar_fotos.py      (fotos nuevas -> WebP con marca de agua)
rem       -- si no hay nada nuevo en por-procesar, continua igual --
rem    4) actualizar_galeria.py  (regenera assets/js/fotos.js)
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizar todo.bat" 3     -> hasta convertir fotos (sin galer¡a)
rem    "actualizar todo.bat" 4     -> todo el flujo (igual que sin n£mero)
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

rem --- elige el interprete de Python (py = el lanzador de Windows; si no, python) ---
set PY=py
where py >nul 2>nul || set PY=python

rem --- paso final por defecto: 4 = todo el flujo; acepta un numero como argumento ---
set PASO_FINAL=4
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-4]$" >nul && set PASO_FINAL=%~1
)

echo === 0^) Consolidando botones del sitio ===
%PY% herramientas\consolidar_sitio.py
if %PASO_FINAL% LSS 1 goto fin
echo.

echo === 1^) Parche WebP del sitio ===
%PY% herramientas\parche_webp.py
if %PASO_FINAL% LSS 2 goto fin
echo.

echo === 2^) Parche de la galeria ===
%PY% herramientas\parche_galeria.py
if %PASO_FINAL% LSS 3 goto fin
echo.

echo === 3^) Convirtiendo fotos nuevas a WebP ===
%PY% herramientas\preparar_fotos.py
if errorlevel 2 (echo Hubo un problema al convertir. Av¡sale a Claude. & goto fin)
if errorlevel 1 echo   ^(no habia fotos nuevas: continuo con la galeria^)
if %PASO_FINAL% LSS 4 goto fin
echo.

echo === 4^) Actualizando la galeria ===
%PY% herramientas\actualizar_galeria.py

:fin
echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
