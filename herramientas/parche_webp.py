"""Permite que el sitio (assets/js/jfz.js) reconozca fotos .webp en el carrito. Se puede ejecutar muchas veces sin problema."""
import re
from pathlib import Path

ruta = Path(__file__).resolve().parent.parent / "assets" / "js" / "jfz.js"
s = ruta.read_text(encoding="utf-8")
cambios = [
    (r'f.replace(/\.jpg$/i, "")', r'f.replace(/\.(jpe?g|png|webp)$/i, "")'),
    (r'/^IMG_(\d+)\.jpg$/i', r'/^IMG_(\d+)\.(?:jpe?g|png|webp)$/i'),
]
hecho = 0
for viejo, nuevo in cambios:
    if viejo in s:
        s = s.replace(viejo, nuevo); hecho += 1
    elif nuevo not in s:
        print("AVISO: no encontre un texto esperado en jfz.js (¿lo editaste?). Avisale a Claude.")
if hecho:
    ruta.write_text(s, encoding="utf-8")
    print(f"Parche WebP aplicado ({hecho} cambios).")
else:
    print("Parche WebP: ya estaba aplicado.")
