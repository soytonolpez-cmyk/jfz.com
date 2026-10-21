"""Convierte tus fotos terminadas a WebP (liviano), con marca de agua, y las deja en fotos/galeria/.

Flujo normal (doble clic en herramientas/actualizacion_definitiva.bat, que llama a este script):
  1. Mete tus fotos DENTRO de "por-procesar", en una o varias carpetas.
     Ejemplos:  por-procesar/t4/IMG_6001.jpg   o   por-procesar/t4/IMG_6001.CR2
     Tambien sirve por-procesar/foto-suelta.jpg (una carpeta virtual "_sueltas").
     Se aceptan JPG/PNG/TIFF/HEIC y RAW de camara profesional (.CR2 .CR3 .NEF .ARW .RAF .DNG .RW2 .ORF .PEF).
     Los RAW se revelan aqui mismo (con la fecha EXIF original) -> JPG temporal -> WebP.
  2. Cada foto sale a  fotos/galeria/IMG_6001.webp  (la unica carpeta que muestra la galeria
     del sitio; si ya existe una foto con ese nombre se agrega _1, _2... detras).
     Las fechas EXIF se registran solas en fotos/fechas.txt para que la galeria las muestre.
  3. El boton unico regenera assets/js/fotos.js al final: no hay que hacer nada mas.
La carpeta "por-procesar" NO se sube a GitHub (asi tus originales quedan solo en tu PC).
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


def _normalizar_fecha(txt):
    """Pasa 'AAAA:MM:DD HH:MM:SS' o 'AAAA-MM-DD...' a 'AAAA-MM-DD' (o None si no es valida)."""
    f = str(txt or "").strip()[:10].replace("/", "-").replace(":", "-")
    if len(f) == 10 and f[4] == "-" and f[7] == "-":
        return f
    return None


def _fecha_cr2_muy_grande(origen):
    """Plan B para CR2 que PIL no puede abrir (mas de 65535 px por lado): lee la fecha del EXIF crudo.

    Recorre las cadenas de IFD/TIFF (incluidas sub-IFDs, como la IFD Exif donde Canon/Nikon/Sony
    guardan DateTimeOriginal) buscando la fecha de toma. Solo se leen cadenas coherentes: si una
    entrada parece corrupta se ignora ese nivel sin perder lo ya encontrado.
    """
    try:
        datos = origen.read_bytes()
        if len(datos) < 16:
            return None
        endian = "<" if datos[6:8] == b"II" else ">"
        u16 = lambda b, o: int.from_bytes(b[o:o + 2], endian)
        u32 = lambda b, o: int.from_bytes(b[o:o + 4], endian)

        def leer_ifd(bloque, base):
            """Devuelve (dict tag->valor, next_offset) o None si la cadena parece invalida."""
            try:
                n = u16(bloque, 0)
                if n > 600 or len(bloque) < 2 + 12 * n:
                    return None
                salida = {}
                for i in range(n):
                    e = 2 + 12 * i
                    tag, typ, cnt = u16(bloque, e), u16(bloque, e + 2), u32(bloque, e + 4)
                    if typ == 2:                                   # ASCII
                        tam = max(cnt, 1)
                        if tam <= 4:
                            txt = bloque[e + 8:e + 8 + tam]
                        elif 4 + tam <= len(bloque):               # puntero a zona de datos
                            off = u32(bloque, e + 8)
                            if not (off < base or off - base + tam <= len(bloque)):
                                continue
                            txt = bloque[off - base:off - base + tam]
                        else:
                            continue
                        v = txt.split(b"\x00")[0].decode("ascii", "ignore").strip()
                        if v:
                            salida[tag] = v
                    elif tag in (0x8769, 0xA005):                  # punteros ExifIFD / InteropIFD
                        salida[tag] = u32(bloque, e + 8)
                nxt = u32(bloque, 2 + 12 * n) if len(bloque) >= 2 + 12 * n + 4 else 0
                return salida, nxt
            except Exception:
                return None

        cola = [int.from_bytes(datos[8:12], endian)]   # cabecera TIFF -> IFD0 (offset 8 en CR2)
        vistos = set()
        while cola:
            off = cola.pop(0)
            if off in vistos or not (0 < off < len(datos) - 2):
                continue
            vistos.add(off)
            r = leer_ifd(datos[off:], off)
            if not r:
                continue
            tags, nxt = r
            for tag in (36867, 36868, 306):             # DateTimeOriginal / Digitized / DateTime
                f = _normalizar_fecha(tags.get(tag))
                if f:
                    return f
            for tag in (0x8769, 0xA005):
                if isinstance(tags.get(tag), int):
                    cola.append(tags[tag])
            if nxt:
                cola.append(nxt)
    except Exception:
        pass
    return None


def _guardar_jpg(im, destino_jpg, exif=None):
    """Guarda RGB como JPEG calidad 95, adjuntando el EXIF si el formato lo permite."""
    extra = {"exif": exif} if exif else {}
    try:
        im.save(destino_jpg, "JPEG", quality=95, **extra)
    except (ValueError, TypeError):             # algunos EXIF no son validos para JPEG
        im.save(destino_jpg, "JPEG", quality=95)


def revelar_raw(origen, destino_jpg):
    """RAW (CR2/CR3/NEF/ARW/DNG...) -> JPG temporal. Devuelve la fecha 'AAAA-MM-DD' del RAW o None.

    Ruta principal: rawpy/LibRaw (revelado completo). Si falta rawpy o el archivo puntual
    da error, se intenta una via alternativa con Pillow (lee el JPG embebido del RAW),
    y para CR2 modernos muy grandes existe un lector directo del EXIF para la fecha.
    """
    import io
    fecha = None
    jpg = None
    if rawpy is not None:
        try:
            with rawpy.imread(str(origen)) as r:
                jpg = r.postprocess(use_auto_wb=True)          # revelado basico de LibRaw
                try:
                    fecha = _normalizar_fecha(getattr(r.other, "capture_time", ""))
                except Exception:
                    fecha = None
        except Exception as e:
            print(f"    AVISO: rawpy no pudo revelar {origen.name} ({e}); pruebo la via alternativa.")
    if jpg is None:                                           # via alternativa: Pillow
        try:
            with Image.open(origen) as im:
                exif = im.getexif()
                try:                                # DateTimeOriginal vive en la IFD Exif (0x8769)
                    sub = exif.get_ifd(0x8769)
                    for tag in (36867, 36868, 306):
                        if sub.get(tag):
                            fecha = _normalizar_fecha(sub[tag]); break
                except Exception:
                    fecha = None
                if not fecha:
                    for tag in (36867, 36868, 306):
                        if exif.get(tag):
                            fecha = _normalizar_fecha(exif[tag]); break
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=95)
                jpg = buf.getvalue()
        except Exception as e:
            print(f"    AVISO: Pillow tampoco abrio {origen.name} ({type(e).__name__}: {e}).")
            if origen.suffix.lower() == ".cr2":               # plan B solo para la fecha
                fecha = _fecha_cr2_muy_grande(origen)
            return None
    if jpg is None:
        if rawpy is None:
            print(f"    AVISO: {origen.name} es RAW y te falta la libreria. Instala: py -m pip install rawpy")
        return None
    _guardar_jpg(Image.open(io.BytesIO(jpg)), destino_jpg)
    return fecha


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


DESTINO_GALERIA = SALIDA / "galeria"   # unica carpeta que muestra la galeria del sitio


def _nombre_unico(stem):
    """fotos/galeria/<stem>.webp; si ya existe uno, agrega _1, _2... detras."""
    destino = DESTINO_GALERIA / f"{stem}.webp"
    i = 1
    while destino.exists():
        destino = DESTINO_GALERIA / f"{stem}_{i}.webp"
        i += 1
    return destino


def main():
    ENTRADA.mkdir(exist_ok=True)
    # Colectar TODAS las fotos de por-procesar/ (recursivo), sin exigir subcarpetas.
    grupos = {}   # clave de subcarpeta -> [archivos]
    for p in sorted(ENTRADA.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in EXTENSIONES and ext not in EXT_RAW:
            continue
        rel = p.relative_to(ENTRADA)
        clave = rel.parts[0] if len(rel.parts) > 1 else "_sueltas"
        grupos.setdefault(clave, []).append(p)
    if not grupos:
        print("No hay fotos dentro de 'por-procesar'. Mete ahi tus fotos terminadas")
        print("(sueltas o en carpetas, ej. por-procesar/t4/) y vuelve a ejecutar.")
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
        try:
            resp = input("Escribe SI para continuar de todos modos, o pulsa Enter para cancelar: ").strip().upper()
        except EOFError:
            resp = ""
        if resp != "SI":
            print("Cancelado. Pon tu marca de agua (PNG transparente) en herramientas/marca_agua.png y repite.")
            return 1
    DESTINO_GALERIA.mkdir(parents=True, exist_ok=True)
    total = 0
    for clave in sorted(grupos):
        archivos = grupos[clave]
        nuevas = 0
        temporales = []
        fallan_raw = []
        for f in archivos:
            origen = f
            if any((DESTINO_GALERIA / f.stem).with_suffix(e).exists() for e in (".webp", ".jpg", ".jpeg", ".png")):
                continue                          # esa foto ya esta en la galeria: no se repite
            try:
                if f.suffix.lower() in EXT_RAW:   # RAW -> JPG temporal (primero JPG, luego WebP)
                    if rawpy is None:
                        print(f"  AVISO: {f.name} es RAW y te falta la libreria. Instala: py -m pip install rawpy")
                        continue
                    tmp = RAIZ / "herramientas" / "__tmp__" / f"{clave}_{f.stem}.jpg"
                    tmp.parent.mkdir(exist_ok=True)
                    fecha_raw = revelar_raw(f, tmp)
                    if not tmp.exists():
                        fallan_raw.append(f.name)          # no se pudo revelar: queda para la proxima
                        continue
                    origen = tmp
                    temporales.append(tmp)
                    if fecha_raw:
                        registrar_fecha("galeria", f.stem, fecha_raw)
                else:
                    # Las JPG/PNG/HEIC tambien merecen su fecha registrada (si traen EXIF).
                    try:
                        with Image.open(origen) as im:
                            ex = im.getexif()
                            sub = ex.get_ifd(0x8769)
                            for tag in (36867, 36868, 306):
                                v = _normalizar_fecha(sub.get(tag) or ex.get(tag))
                                if v:
                                    registrar_fecha("galeria", f.stem, v)
                                    break
                    except Exception:
                        pass
                destino = _nombre_unico(f.stem)
                convertir(origen, destino, marca)
                nuevas += 1
                print(f"  OK  {f.name} -> fotos/galeria/{destino.name}  ({destino.stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  ERROR con {f.name}: {e}")
        for tmp in temporales:
            try:
                tmp.unlink()                      # borra los JPG temporales
            except OSError:
                pass
        total += nuevas
        skip = len(archivos) - nuevas - len(fallan_raw)
        print(f"{clave}: {nuevas} fotos nuevas ({skip} ya existian).")
        if fallan_raw:
            print(f"  ATENCION: no se pudieron revelar {len(fallan_raw)} RAW: {', '.join(fallan_raw[:6])}")
            print("               Instala/actualiza la libreria (py -m pip install -U rawpy) o exporta esos")
            print("               archivos a JPG desde tu editor y vuelve a ejecutar (no se pierden).")
    print(f"Listo: {total} fotos convertidas a fotos/galeria/ (con marca de agua).")
    print("Ahora el boton unico regenera la galeria; tus originales siguen en por-procesar/ para el pedido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
