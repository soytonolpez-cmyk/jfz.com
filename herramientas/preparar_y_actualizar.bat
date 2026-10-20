@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
echo === 0/3 Consolidando botones del sitio ===
py herramientas\consolidar_sitio.py
echo.
echo === 1/3 Parche del sitio ===
py herramientas\parche_webp.py
py herramientas\parche_galeria.py
echo.
echo === 2/3 Convirtiendo fotos nuevas a WebP ===
py herramientas\preparar_fotos.py
if errorlevel 1 goto fin
echo.
echo === 3/3 Actualizando la galeria ===
py herramientas\actualizar_galeria.py
:fin
echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
