"""Pasa las fotos de fotos/Legado/ a por-procesar/legado/ y quita 'Legado' del sitio.

Para cuando quieras jubilarya la carpeta Legado (los originales quedan solo en tu PC):
  py herramientas/migrar_legado.py          -> copia las .webp a por-procesar/legado/
Luego: borra la carpeta fotos/Legado, borra la linea 'Legado | ...' de fotos/trimestres.txt
y ejecuta "actualizar todo.bat". Las fechas ya estan en fotos/fechas.txt si las tenia.
"""
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "fotos" / "Legado"
DESTINO = RAIZ / "por-procesar" / "legado"

if not ORIGEN.exists():
    print("No existe fotos/Legado: nada que migrar.")
elif input(f"Copiar {len(list(ORIGEN.iterdir()))} fotos de fotos/Legado a por-procesar/legado (sin borrar el origen). Escribe SI para continuar: ").strip().upper() != "SI":
    print("Cancelado.")
else:
    DESTINO.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(ORIGEN.iterdir()):
        if f.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png"):
            destino = DESTINO / f.name
            if not destino.exists():
                shutil.copy2(f, destino); n += 1
    print(f"Listo: {n} fotos copiadas a por-procesar/legado/.")
    print("Ahora puedes borrar la carpeta fotos/Legado y su linea en fotos/trimestres.txt,")
    print("y ejecutar herramientas/\"actualizar todo.bat\".")
