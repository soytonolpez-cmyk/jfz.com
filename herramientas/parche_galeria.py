"""Conecta galeria-plus (mosaico + indicador de fecha) a gallery.html. Se puede ejecutar muchas veces sin problema."""
from pathlib import Path

ruta = Path(__file__).resolve().parent.parent / "gallery.html"
s = ruta.read_text(encoding="utf-8")
pares = [
    ('<link href="assets/css/jfz.css" rel="stylesheet">', '<link href="assets/css/galeria-plus.css" rel="stylesheet">'),
    ('<script src="assets/js/jfz.js"></script>', '<script src="assets/js/galeria-plus.js"></script>'),
]
hecho = 0
for ancla, nueva in pares:
    if nueva in s:
        continue
    if ancla not in s:
        print("AVISO: no encontre " + ancla + " en gallery.html. Avisale a Claude."); continue
    s = s.replace(ancla, ancla + "\n  " + nueva); hecho += 1
if hecho:
    ruta.write_text(s, encoding="utf-8"); print(f"Galeria conectada ({hecho} cambios).")
else:
    print("Galeria: ya estaba conectada.")
