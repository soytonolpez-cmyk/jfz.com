"""Convierte tus fotos terminadas a WebP (liviano), con marca de agua, y las deja en fotos/<carpeta>/.

Como se usa (lo normal es hacerlo con el archivo preparar_y_actualizar.bat, doble clic):
  1. Mete tus fotos DENTRO de "por-procesar", en una carpeta por trimestre.
     Ejemplos:  por-procesar/t4/IMG_6001.jpg   o   por-procesar/t4/IMG_6001.CR2
     Se aceptan JPG/PNG/TIFF y RAW de camara profesional (.CR2 .CR3 .NEF .ARW .RAF .DNG .RW2 .ORF .PEF).
     Los RAW se revelan aqui mismo (con la fecha EXIF original) -> JPG temporal -> WebP.
  2. Ejecuta este programa. Crea  fotos/t4/IMG_6001.webp
La carpeta "por-procesar" NO se sube a GitHub (asi tus originales quedan solo en tu PC).
Si usaste antes la carpeta fotos/Legado: pasa su contenido a por-procesar (o ejecuta
herramientas/migrar_legado.py) y borra la linea "Legado | ..." de fotos/trimestres.txt.
"""
from pathlib import Path
from PIL import Image, ImageOps

try:
    import rawpy          # revelado RAW: py -m pip install rawpy
except ImportError:
    rawpy = None
try:
    import pillow_heif    # HEIC/HEIF de iPhone: py -m pip install pillow-heif
except ImportError:
    pillow_heif = None
else:
    pillow_heif.register_heif_opener()

# ------------------------- AJUSTES (puedes cambiarlos) -------------------------
CALIDAD = 80            # 70 = mas liviano, 85 = mas calidad. Recomendado: 80
LADO_MAXIMO = 1920      # lado mas largo en pixeles. 0 = no reducir
ANCHO_MARCA = 0.6      # ancho de la marca de agua = 60% del ancho de la foto (0.35 = mas pequena)
OPACIDAD = 0.5          # 1 = tal como es tu PNG; mas de 1 = mas visible; menos de 1 = mas tenue
POSICION = "centro"     # "centro" o "abajo-derecha"
# -------------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "por-procesar"
SALIDA = RAIZ / "fotos"
MARCA = RAIZ / "herramientas" / "marca_agua.png"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".heif"}
EXT_RAW = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng", ".rw2", ".orf", ".pef", ".raw"}
Image.MAX_IMAGE_PIXELS = None


def revelar_raw(origen, destino_jpg):
    """RAW (CR2/NEF/ARW...) -> JPG temporal. Devuelve la fecha 'AAAA-MM-DD' del RAW o None."""
    import io
    with rawpy.imread(str(origen)) as r:
        jpg = r.postprocess(use_auto_wb=True)          # revelado basico de LibRaw
    try:
        meta = r.other
        fecha = str(getattr(meta, "capture_time", "") or "").strip()[:10].replace("/", "-")
    except Exception:
        fecha = ""
    if not (len(fecha) == 10 and fecha[4] == "-" and fecha[7] == "-"):
        fecha = ""
    Image.open(io.BytesIO(jpg)).save(destino_jpg, "JPEG", quality=95)
    return fecha or None


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


def registrar_fecha(carpeta, nombre_sin_ext, fecha):
    """Agrega una linea a fotos/fechas.txt para que la foto conserve su fecha (los RAW no traen EXIF visible)."""
    txt = RAIZ / "fotos" / "fechas.txt"
    linea = f"{carpeta} | {nombre_sin_ext} | {fecha}\n"
    existentes = txt.read_text(encoding="utf-8").splitlines() if txt.exists() else []
    for l in existentes:
        p = [x.strip() for x in l.split("|")]
        if len(p) == 3 and p[0].lower() == carpeta.lower() and p[1].lower() == nombre_sin_ext.lower():
            return                      # ya estaba registrada
    with txt.open("a", encoding="utf-8") as f:
        f.write(linea)


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
        archivos = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES | EXT_RAW)
        destino_dir = SALIDA / carpeta.name
        destino_dir.mkdir(exist_ok=True)
        nuevas = 0
        temporales = []
        for f in archivos:
            destino = destino_dir / (f.stem + ".webp")
            origen = f
            if destino.exists():
                continue                          # ya estaba hecha: no se repite
            try:
                if f.suffix.lower() in EXT_RAW:   # RAW -> JPG temporal (primero JPG, luego WebP)
                    if rawpy is None:
                        print(f"  AVISO: {f.name} es RAW y te falta la libreria. Instala: py -m pip install rawpy")
                        continue
                    tmp = RAIZ / "herramientas" / "__tmp__" / f"{carpeta.name}_{f.stem}.jpg"
                    tmp.parent.mkdir(exist_ok=True)
                    fecha_raw = revelar_raw(f, tmp)
                    origen = tmp
                    temporales.append(tmp)
                    if fecha_raw:
                        registrar_fecha(carpeta.name, f.stem, fecha_raw)
                convertir(origen, destino, marca)
                nuevas += 1
                print(f"  OK  {carpeta.name}/{destino.name}  ({destino.stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  ERROR con {f.name}: {e}")
        for tmp in temporales:
            try:
                tmp.unlink()                      # borra los JPG temporales
            except OSError:
                pass
        total += nuevas
        print(f"{carpeta.name}: {nuevas} fotos nuevas ({len(archivos) - nuevas} ya existian).")
        if carpeta.name not in [l.split("|")[0].strip() for l in registradas.splitlines() if "|" in l]:
            print(f"  AVISO: agrega esta linea en fotos/trimestres.txt para que se vea en el sitio:")
            print(f"         {carpeta.name} | Titulo que quieras (ej. 4to Trimestre 2026)")
    print(f"Listo: {total} fotos convertidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
