"""Actualiza la galería leyendo las carpetas de fotos.

Uso (desde una consola dentro de la carpeta del proyecto):
    python herramientas/actualizar_galeria.py     (en Windows también: py herramientas/actualizar_galeria.py)

Lee   fotos/trimestres.txt        (carpeta | Título)
      fotos/fechas.txt            (opcional: fechas puestas a mano, ver el archivo)
      fotos/etiquetas.txt         (opcional: etiquetas para el buscador, ver el archivo)
y las fotos de cada carpeta       fotos/<carpeta>/
Crea  assets/js/fotos.js          (lo que usa el sitio)

La fecha de cada foto sale de: 1) fotos/fechas.txt, 2) la fecha guardada dentro de la foto (EXIF).
Las etiquetas salen de fotos/etiquetas.txt (formato: fotos | moto,casco,caras).
"""
import json
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

RAIZ = Path(__file__).resolve().parent.parent
FOTOS = RAIZ / "fotos"
EXT = (".jpg", ".jpeg", ".png", ".webp")


def fecha_exif(ruta):
    """Devuelve 'AAAA-MM-DD' desde los datos internos de la foto, o None."""
    if Image is None:
        return None
    try:
        with Image.open(ruta) as im:
            ex = im.getexif()
            valores = [ex.get_ifd(0x8769).get(36867), ex.get_ifd(0x8769).get(36868), ex.get(306)]
        for v in valores:
            if v:
                return datetime.strptime(str(v)[:10], "%Y:%m:%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def leer_fechas_manuales():
    """fotos/fechas.txt -> {carpeta: [(lista_de_fotos_o_None, 'AAAA-MM-DD'), ...]}"""
    reglas, ruta = {}, FOTOS / "fechas.txt"
    if not ruta.exists():
        return reglas
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [x.strip() for x in linea.split("|")]
        try:
            if len(partes) != 3:
                raise ValueError("deben ser 3 partes separadas por |")
            datetime.strptime(partes[2], "%Y-%m-%d")
        except ValueError as e:
            print(f"AVISO fechas.txt línea {n}: la ignoro ({e}). Formato: carpeta | fotos | AAAA-MM-DD")
            continue
        reglas.setdefault(partes[0].lower(), []).append((partes[1], partes[2]))
    return reglas


def fechas_de_seccion(carpeta, fotos, rutas, reglas):
    """Calcula la fecha de cada foto: 1) reglas de fechas.txt, 2) EXIF. Una regla con * vale solo para las fotos que aun no tienen fecha."""
    stems = [Path(f).stem for f in fotos]
    resultado = {f: fecha_exif(rutas / f) for f in fotos}
    puestas = set()
    pendientes = []
    for selector, fecha in reglas.get(carpeta.lower(), []):
        if selector == "*":
            pendientes.append(fecha)
            continue
        ext = [s.strip() for s in selector.replace(" a ", "|").split("|")]
        try:
            ini, fin = stems.index(ext[0]), stems.index(ext[-1])
        except ValueError:
            print(f"AVISO fechas.txt: en '{carpeta}' no encuentro '{selector}'. Revisa los nombres (sin .jpg/.webp).")
            continue
        for i in range(min(ini, fin), max(ini, fin) + 1):
            resultado[fotos[i]] = fecha
            puestas.add(fotos[i])
    for fecha in pendientes:
        for f in fotos:
            if f not in puestas and not resultado[f]:
                resultado[f] = fecha
    return {f: d for f, d in resultado.items() if d}


def leer_etiquetas():
    """fotos/etiquetas.txt -> [(selector, [etiqueta, ...]), ...] para TODAS las carpetas.

    Formato de linea:  fotos | moto,casco,caras   (sin carpeta: las etiquetas valen en todo el sitio)
      - fotos: un nombre sin .jpg/.webp, o un rango con la palabra " a ".
    El orden importa: la ultima regla que toque una foto reemplaza sus etiquetas.
    """
    reglas, ruta = [], FOTOS / "etiquetas.txt"
    if not ruta.exists():
        return reglas
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [x.strip() for x in linea.split("|")]
        if len(partes) != 2:
            print(f"AVISO etiquetas.txt linea {n}: la ignoro. Formato: fotos | moto,casco")
            continue
        sel, lista = partes[0], [e.strip().lower() for e in partes[1].replace(";", ",").split(",") if e.strip()]
        if not sel or not lista:
            print(f"AVISO etiquetas.txt linea {n}: falta la lista de fotos o las etiquetas.")
            continue
        reglas.append((sel, lista))
    return reglas


def etiquetas_de_seccion(fotos, rutas, reglas):
    """Calcula las etiquetas de cada foto desde fotos/etiquetas.txt -> {foto: [etiqueta, ...]}"""
    stems = [Path(f).stem for f in fotos]
    resultado = {}
    for selector, lista in reglas:
        ext = [s.strip() for s in selector.replace(" a ", "|").split("|")]
        try:
            ini, fin = stems.index(ext[0]), stems.index(ext[-1])
        except ValueError:
            continue   # la regla no pertenece a esta seccion: se ignora en silencio
        for i in range(min(ini, fin), max(ini, fin) + 1):
            resultado[fotos[i]] = list(lista)
    return {f: v for f, v in resultado.items() if v}


ETIQUETAS_PROHIBIDAS = {"moto", "motos", "casco", "cascos", "cara", "caras"}   # no se muestran en el sitio (a pedido del dueño)


def limpiar_etiquetas(ets):
    """Quita de las etiquetas de cada foto las palabras prohibidas (moto/casco/caras...)."""
    return {f: [e for e in v if e not in ETIQUETAS_PROHIBIDAS] for f, v in ets.items()}


reglas = leer_fechas_manuales()
etiquetas_reglas = leer_etiquetas()
secciones = []
for linea in (FOTOS / "trimestres.txt").read_text(encoding="utf-8").splitlines():
    linea = linea.strip()
    if not linea or linea.startswith("#") or "|" not in linea:
        continue
    carpeta, titulo = [x.strip() for x in linea.split("|", 1)]
    reales = {d.name.lower(): d.name for d in FOTOS.iterdir() if d.is_dir()}
    carpeta = reales.get(carpeta.lower(), carpeta)   # GitHub distingue Legado de legado: se usa el nombre real
    ruta = FOTOS / carpeta
    ruta.mkdir(exist_ok=True)
    fotos = sorted(p.name for p in ruta.iterdir() if p.suffix.lower() in EXT)
    seccion = {"id": carpeta, "titulo": titulo, "carpeta": carpeta, "fotos": fotos}
    fechas = fechas_de_seccion(carpeta, fotos, ruta, reglas)
    if fechas:
        seccion["fechas"] = fechas
    ets = limpiar_etiquetas(etiquetas_de_seccion(fotos, ruta, etiquetas_reglas))
    ets = {f: v for f, v in ets.items() if v}   # descartar fotos que se quedaron sin etiquetas
    if ets:
        seccion["etiquetas"] = ets
        seccion["todas_etiquetas"] = sorted({e for v in ets.values() for e in v})
    secciones.append(seccion)
    print(f"{titulo}: {len(fotos)} fotos ({len(fechas)} con fecha, {len(ets)} con etiquetas)")

(RAIZ / "assets/js/fotos.js").write_text(
    "/* ARCHIVO GENERADO por herramientas/actualizar_galeria.py - no lo edites a mano */\n"
    "window.JFZ_FOTOS = " + json.dumps(secciones, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
if Image is None:
    print("AVISO: no tienes Pillow instalado, no pude leer fechas dentro de las fotos (py -m pip install Pillow).")
print("Listo: assets/js/fotos.js actualizado.")
