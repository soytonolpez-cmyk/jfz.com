"""Actualiza la galería leyendo las carpetas de fotos.

Uso (desde una consola dentro de la carpeta del proyecto):
    python herramientas/actualizar_galeria.py     (en Windows también: py herramientas/actualizar_galeria.py)

Lee   fotos/trimestres.txt        (carpeta | Título)
y las fotos de cada carpeta       fotos/<carpeta>/
Crea  assets/js/fotos.js          (lo que usa el sitio)
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FOTOS = RAIZ / "fotos"
secciones = []
for linea in (FOTOS / "trimestres.txt").read_text(encoding="utf-8").splitlines():
    linea = linea.strip()
    if not linea or linea.startswith("#") or "|" not in linea:
        continue
    carpeta, titulo = [x.strip() for x in linea.split("|", 1)]
    ruta = FOTOS / carpeta
    ruta.mkdir(exist_ok=True)
    fotos = sorted(p.name for p in ruta.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    secciones.append({"id": carpeta, "titulo": titulo, "carpeta": carpeta, "fotos": fotos})
    print(f"{titulo}: {len(fotos)} fotos")

(RAIZ / "assets/js/fotos.js").write_text(
    "/* ARCHIVO GENERADO por herramientas/actualizar_galeria.py - no lo edites a mano */\n"
    "window.JFZ_FOTOS = " + json.dumps(secciones, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
print("Listo: assets/js/fotos.js actualizado.")
