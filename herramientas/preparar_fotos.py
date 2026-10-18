"""Convierte tus fotos terminadas a WebP (liviano), con marca de agua, y las deja en fotos/<carpeta>/.

Como se usa (lo normal es hacerlo con el archivo preparar_y_actualizar.bat, doble clic):
  1. Exporta tus fotos desde RawTherapee como JPG (o TIFF/PNG) a una carpeta DENTRO de "por-procesar",
     con el mismo nombre de la carpeta del trimestre.  Ejemplo:  por-procesar/t4/IMG_6001.jpg
  2. Ejecuta este programa. Crea  fotos/t4/IMG_6001.webp
La carpeta "por-procesar" NO se sube a GitHub (asi tus originales sin marca de agua quedan solo en tu PC).
"""
from pathlib import Path
from PIL import Image, ImageOps

# ------------------------- AJUSTES (puedes cambiarlos) -------------------------
CALIDAD = 80            # 70 = mas liviano, 85 = mas calidad. Recomendado: 80
LADO_MAXIMO = 1920      # lado mas largo en pixeles. 0 = no reducir
ANCHO_MARCA = 1      # ancho de la marca de agua = 60% del ancho de la foto (0.35 = mas pequena)
OPACIDAD = 0.01          # 1 = tal como es tu PNG; mas de 1 = mas visible; menos de 1 = mas tenue
POSICION = "centro"     # "centro" o "abajo-derecha"
# -------------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "por-procesar"
SALIDA = RAIZ / "fotos"
MARCA = RAIZ / "herramientas" / "marca_agua.png"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
Image.MAX_IMAGE_PIXELS = None


def poner_marca(im, marca):
    w = max(1, int(im.width * ANCHO_MARCA))
    h = max(1, int(marca.height * w / marca.width))
    m = marca.resize((w, h), Image.LANCZOS)
    m.putalpha(m.getchannel("A").point(lambda a: min(255, int(a * OPACIDAD))))
    if POSICION == "abajo-derecha":
        pos = (im.width - w - int(im.width * 0.03), im.height - h - int(im.width * 0.03))
    else:
        pos = ((im.width - w) // 2, (im.height - h) // 2)
    base = im.convert("RGBA")
    base.alpha_composite(m, (max(0, pos[0]), max(0, pos[1])))
    return base.convert("RGB")


def convertir(origen, destino, marca):
    with Image.open(origen) as im:
        exif = im.getexif()                      # aqui viaja la fecha de la foto
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)         # endereza la foto segun la camara
        if 274 in exif:
            del exif[274]                        # ya enderezada: se quita la orientacion
        im = im.convert("RGB")
        if LADO_MAXIMO:
            im.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
        if marca is not None:
            im = poner_marca(im, marca)
        extra = {"icc_profile": icc} if icc else {}
        im.save(destino, "WEBP", quality=CALIDAD, method=6, exif=exif, **extra)


def main():
    ENTRADA.mkdir(exist_ok=True)
    carpetas = sorted(p for p in ENTRADA.iterdir() if p.is_dir())
    if not carpetas:
        print("No hay carpetas dentro de 'por-procesar'. Crea una (por ejemplo t4) y mete ahi tus fotos.")
        return 1
    marca = None
    if MARCA.exists():
        marca = Image.open(MARCA).convert("RGBA")
        caja = marca.getchannel("A").getbbox()      # quita los bordes transparentes para centrar bien
        if caja:
            marca = marca.crop(caja)
        print(f"Marca de agua: {marca.width}x{marca.height} px, una sola, en el {POSICION}.")
        if marca.width > 1500 or marca.height > 1500:
            print("AVISO: tu marca_agua.png es enorme. Debe ser UN solo logo, no una imagen con el logo repetido.")
    else:
        print("!! No encontre herramientas/marca_agua.png: las fotos saldrian SIN marca de agua.")
        print("!! Tu repositorio es publico: cualquiera podria descargarlas limpias.")
        if input("Escribe SI para continuar de todos modos, o pulsa Enter para cancelar: ").strip().upper() != "SI":
            print("Cancelado. Pon tu marca de agua (PNG transparente) en herramientas/marca_agua.png y repite.")
            return 1
    registradas = (SALIDA / "trimestres.txt").read_text(encoding="utf-8")
    total = 0
    for carpeta in carpetas:
        fotos = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES)
        destino_dir = SALIDA / carpeta.name
        destino_dir.mkdir(exist_ok=True)
        nuevas = 0
        for f in fotos:
            destino = destino_dir / (f.stem + ".webp")
            if destino.exists():
                continue                          # ya estaba hecha: no se repite
            try:
                convertir(f, destino, marca)
                nuevas += 1
                print(f"  OK  {carpeta.name}/{destino.name}  ({destino.stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  ERROR con {f.name}: {e}")
        total += nuevas
        print(f"{carpeta.name}: {nuevas} fotos nuevas ({len(fotos) - nuevas} ya existian).")
        if carpeta.name not in [l.split("|")[0].strip() for l in registradas.splitlines() if "|" in l]:
            print(f"  AVISO: agrega esta linea en fotos/trimestres.txt para que se vea en el sitio:")
            print(f"         {carpeta.name} | Titulo que quieras (ej. 4to Trimestre 2026)")
    print(f"Listo: {total} fotos convertidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
