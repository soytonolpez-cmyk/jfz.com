"""Pone la marca de agua (texto repetido en diagonal) a las fotos y las deja livianas.

Uso, desde una consola dentro de la carpeta del proyecto:
    python herramientas/marca_de_agua.py  CARPETA_CON_ORIGINALES  CARPETA_DESTINO

Ejemplo:
    python herramientas/marca_de_agua.py  C:/Users/TuUsuario/Originales  fotos/t4

- Las fotos originales NO se tocan.
- Las fotos nuevas quedan con el texto repetido en diagonal (difícil de recortar),
  con máximo 1600 px de lado largo, y sin los datos ocultos de la cámara (ubicación, etc.).
Requiere:  pip install pillow
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

TEXTO = "JUANETOFZ  ·  @JUANETO.BIKER"
OPACIDAD = 0.38      # 0.2 = muy suave, 0.6 = muy fuerte
TAMANO = 0.050       # tamaño de la letra respecto al lado corto de la foto
ANGULO = 28
LADO_MAX = 1600

def _bloque(w, h):
    """Un bloque de texto (blanco con sombra) ya rotado."""
    fuente = ImageFont.load_default(size=max(18, int(min(w, h) * TAMANO)))
    x0, y0, x1, y1 = fuente.getbbox(TEXTO)
    tw, th = x1 - x0 + 8, y1 - y0 + 8
    capa = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.text((5, 5), TEXTO, font=fuente, fill=(0, 0, 0, int(255 * OPACIDAD * 0.8)))   # sombra
    d.text((3, 3), TEXTO, font=fuente, fill=(255, 255, 255, int(255 * OPACIDAD)))   # texto
    return capa.rotate(ANGULO, expand=True, resample=Image.BICUBIC)

def marcar(im):
    im = im.convert("RGBA")
    w, h = im.size
    bl = _bloque(w, h)
    pad = max(bl.size)
    capa = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    paso_x, paso_y = int(bl.width * 1.05), int(bl.height * 1.15)
    for fila, y in enumerate(range(0, h + 2 * pad - bl.height, paso_y)):
        desfase = paso_x // 2 if fila % 2 else 0
        for x in range(desfase, w + 2 * pad - bl.width, paso_x):
            capa.alpha_composite(bl, (x, y))
    capa = capa.crop((pad, pad, pad + w, pad + h))
    return Image.alpha_composite(im, capa).convert("RGB")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    origen, destino = Path(sys.argv[1]), Path(sys.argv[2])
    destino.mkdir(parents=True, exist_ok=True)
    fotos = sorted(p for p in origen.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    for i, f in enumerate(fotos, 1):
        with Image.open(f) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((LADO_MAX, LADO_MAX), Image.LANCZOS)
            marcar(im).save(destino / f.name, "JPEG", quality=82, optimize=True, progressive=True)
        print(f"[{i}/{len(fotos)}] {f.name}")
    print("Listo. Ahora ejecuta: python herramientas/actualizar_galeria.py")
