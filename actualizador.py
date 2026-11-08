"""actualizador.py — EL UNICO SCRIPT del flujo de actualizacion (paso 1 + 2 + 3 juntos).

Antes existian tres archivos ("actualizacion definitiva 1/2/3.py"). Quedaron
consolidados aca, en un solo script que se ejecuta de punta a punta:

    python actualizador.py          -> todo el flujo (lo mismo que el boton .bat)
    python actualizador.py 1        -> solo ordenar fotos/ + parches del sitio
    python actualizador.py 2        -> + convertir fotos y espejar la galeria
    python actualizador.py --revertir       -> devuelve Legado/Prueba Trimestre
    python actualizador.py --jubilar-legacy -> jubila esas secciones a mano

QUE HACE (en orden):
  A) ORDENA fotos/: cualquier foto suelta (o en subcarpetas como t4/) se mueve a
     fotos/galeria/. Idempotente.
  B) PARCHES idempotentes del sitio (webp en el carrito, mosaico mejorado,
     estilos) y crea "actualizacion definitive.bat" (el boton de doble clic).
  C) CONVIERTE por-procesar/ a WebP con marca de agua (necesita Pillow;
     opcional rawpy para RAW y pillow-heif para HEIC). Las fechas EXIF se
     registran solas en fotos/fechas.txt.
  D) ESPEJO EXACTO (a pedido): despues de convertir, fotos/galeria/ queda con
     EXACTAMENTE la misma cantidad, numeros y nombres de archivos que haya en
     por-procesar/, todos en formato .webp.
  E) REGENERA assets/js/fotos.js.
  F) LIMPIEZA: elimina los viejos archivos consolidados.
"""
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None
    print('AVISO: falta Pillow (py -m pip install Pillow). La conversion de fotos no funcionara sin ella.')

try:
    import rawpy          # revelado RAW: py -m pip install rawpy
except ImportError:
    rawpy = None

try:
    import pillow_heif    # HEIC/HEIF de iPhone: py -m pip install pillow-heif
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass
except ImportError:
    pillow_heif = None

# =========================================================================
# BARRA DE PROGRESO: tqdm con fallback seguro a porcentaje
# =========================================================================
try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False
    tqdm = None

def _barra_progreso(total, desc):
    """Devuelve un iterable que muestra el avance sobre `total` elementos."""
    if _HAS_TQDM:
        return tqdm(range(total), desc=desc, unit="item", ncols=80)

    class _BarraSimple:
        ANCHO = 10
        def __init__(self, total_, desc_):
            self.total = max(1, total_)
            self.desc = desc_
            self.n = 0

        def __iter__(self):
            for i in range(self.total):
                yield i
                self._avanzar()

        def _avanzar(self):
            self.n += 1
            pct = int(self.n * 100 / self.total)
            lleno = round(self.ANCHO * self.n / self.total)
            barra = "█" * lleno + "░" * (self.ANCHO - lleno)
            print(f"\r{self.desc}: Procesando {self.n} de {self.total} ({pct}%) [{barra}]", end="", flush=True)

        def close(self):
            print()  # salto de linea final del fallback

    return _BarraSimple(total, desc)
# =========================================================================

# RAIZ = carpeta del proyecto (este script vive en la raiz).
RAIZ = Path(__file__).resolve().parent
HERR = RAIZ / "herramientas"
FOTOS = RAIZ / "fotos"
TRIM = RAIZ / "fotos" / "trimestres.txt"
OTRAS = [RAIZ / "fotos" / "fechas.txt"]
ETIQ = RAIZ / "fotos" / "etiquetas.txt"

JUBILAR = ["legado", "Legado", "t9test", "prueba trimestre", "prueba-trimestre"]
FOTOS_PRUEBA = ["img_9001", "img_9002"]
CARPETAS_JUBILADAS = ["legado", "t9test"]
DESTINO_GALERIA = FOTOS / "galeria"
EXT_FOTOS = (".jpg", ".jpeg", ".png", ".webp")
EXT_EXTRA = (".heic", ".heif", ".tif", ".tiff")

MARCA_AGUIO = """AVISO: no encontre marca_agua.png (quedo duplicado en la raiz y en
herramientas/ durante la transicion). El paso 2 avisa si falta; para convertir
necesitas ahi tu logo PNG transparente."""


def _normalizar(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _es_carjeta_jubilada(nombre_carpeta):
    n = _normalizar(nombre_carpeta)
    return ("legado" in n) or ("prueba" in n and "trimestre" in n) or n == "t9test"


EXT_NAVEGADOR = (".jpg", ".jpeg", ".png", ".webp")


def _renombrar_para_navegador(nombre):
    p = Path(nombre)
    if p.suffix.lower() in EXT_NAVEGADOR:
        return nombre
    try:
        from PIL import Image
    except ImportError:
        return nombre
    try:
        import pillow_heif
    except ImportError:
        pillow_heif = None
    if pillow_heif is not None:
        try:
            pillow_heif.register_heif_opener()
        except Exception:
            pass
    try:
        with Image.open(p) as im:
            im.verify()
    except Exception:
        return nombre
    return p.stem + ".jpg"


def _convertir_a_jpg(origen, destino):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return False
    try:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except Exception:
            pass
        with Image.open(origen) as im:
            im = ImageOps.exif_transpose(im)
            if LADO_MAXIMO_FOTO and max(im.size) > LADO_MAXIMO_FOTO:
                im.thumbnail((LADO_MAXIMO_FOTO, LADO_MAXIMO_FOTO))
            if im.mode in ("RGBA", "P", "LA"):
                im = im.convert("RGB")
            # CAMBIO: Calidad reducida a 70
            im.save(destino, "JPEG", quality=70)
        return True
    except Exception:
        return False


LADO_MAXIMO_FOTO = 1920


def _destino_libre(nombre):
    nombre = _renombrar_para_navegador(nombre)
    destino = DESTINO_GALERIA / nombre
    if not destino.exists():
        return destino
    p = Path(nombre)
    i = 1
    while True:
        candidato = DESTINO_GALERIA / f"{p.stem}_{i}{p.suffix}"
        if not candidato.exists():
            return candidato
        i += 1


def _mover_a_galeria(origen, destino_base):
    destino = _destino_libre(destino_base or origen.name)
    try:
        if destino.suffix.lower() == ".jpg" and origen.suffix.lower() not in EXT_FOTOS:
            if _convertir_a_jpg(origen, destino):
                origen.unlink()
                return f"{origen.parent.name}/{origen.name} -> galeria/{destino.name} (convertida a JPG)"
            shutil.move(str(origen), str(DESTINO_GALERIA / origen.name))
            return f"{origen.parent.name}/{origen.name} -> galeria/{origen.name} (no pude convertirla; revisala)"
        shutil.move(str(origen), str(destino))
        return f"{origen.parent.name}/{origen.name} -> galeria/{destino.name}"
    except OSError as e:
        return "__ERROR__ " + str(e)


def ordenar_fotos():
    movidas, avisos = [], []
    if not FOTOS.is_dir():
        return movidas, avisos
    DESTINO_GALERIA.mkdir(exist_ok=True)
    for p in sorted(FOTOS.iterdir()):
        if not p.is_file() or p.suffix.lower() not in (EXT_FOTOS + EXT_EXTRA):
            continue
        res = _mover_a_galeria(p, None)
        if res and res.startswith("__ERROR__"):
            avisos.append(f"No pude mover {p.name}: {res[10:]}")
        elif res:
            movidas.append(res)
    for sub in sorted(FOTOS.iterdir()):
        if not sub.is_dir() or _normalizar(sub.name) == "galeria" or _es_carjeta_jubilada(sub.name):
            continue
        for p in sorted(sub.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (EXT_FOTOS + EXT_EXTRA):
                continue
            res = _mover_a_galeria(p, None)
            if res and res.startswith("__ERROR__"):
                avisos.append(f"No pude mover {sub.name}/{p.name}: {res[10:]}")
            elif res:
                movidas.append(res)
        try:
            if sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()
        except OSError:
            pass
    return movidas, avisos


def mover_fotos_jubiladas():
    movidas, avisos = [], []
    if FOTOS.is_dir():
        for sub in sorted(FOTOS.iterdir()):
            if not sub.is_dir() or not _es_carjeta_jubilada(sub.name):
                continue
            archivos = sorted(p for p in sub.iterdir()
                              if p.is_file() and p.suffix.lower() in (EXT_FOTOS + EXT_EXTRA))
            if not archivos:
                continue
            DESTINO_GALERIA.mkdir(exist_ok=True)
            for foto in archivos:
                res = _mover_a_galeria(foto, None)
                if res and res.startswith("__ERROR__"):
                    avisos.append(f"No pude mover {sub.name}/{foto.name}: {res[10:]}")
                elif res:
                    movidas.append(res)
    for m in movidas:
        print("+ Foto migrada a la galería general: " + m)
    for a in avisos:
        print("AVISO: " + a)
    if not movidas and not avisos:
        print("No quedaban fotos en Legado / Prueba Trimestre (ya estaban en galeria).")
    return len(avisos) == 0


def _es_de_seccion(linea, claves):
    partes = [x.strip() for x in linea.split("|")]
    return bool(partes) and partes[0].lower() in {c.lower() for c in claves}


def jubilar():
    cambiados = []
    claves = {c.lower() for c in JUBILAR}

    if TRIM.exists():
        lineas = TRIM.read_text(encoding="utf-8").splitlines()
        nueva = []
        for ln in lineas:
            if _es_de_seccion(ln.strip(), claves) and not ln.strip().startswith("#"):
                nueva.append("# JUBILADO (antes en la galería): " + ln)
            else:
                nueva.append(ln)
        if not any(_es_de_seccion(l.strip(), ["galeria"]) for l in nueva
                   if l.strip() and not l.strip().startswith("#")):
            nueva.append("galeria | Galería")
            cambiados.append("trimestres.txt: agregada la sección «galeria» (recibe las fotos jubiladas)")
        if nueva != lineas:
            TRIM.write_text("\n".join(nueva) + "\n", encoding="utf-8")
            cambiados.append("trimestres.txt: Legado y Prueba Trimestre fuera de la galería")

    for ruta in OTRAS:
        if not ruta.exists():
            continue
        ls = ruta.read_text(encoding="utf-8").splitlines()
        out, tocado = [], False
        for ln in ls:
            s = ln.strip()
            partes = [x.strip() for x in s.split("|")]
            if s.startswith("#"):
                out.append(ln)
                continue
            if len(partes) == 3 and _es_de_seccion(s, claves):
                out.append("# JUBILADO: " + ln)
                tocado = True
            else:
                out.append(ln)
        if tocado:
            ruta.write_text("\n".join(out) + "\n", encoding="utf-8")
            cambiados.append(f"{ruta.name}: reglas de las secciones jubiladas comentadas")

    if ETIQ.exists():
        ls = ETIQ.read_text(encoding="utf-8").splitlines()
        out, quitadas = [], 0
        for ln in ls:
            s = ln.strip()
            partes = [x.strip() for x in s.split("|")]
            if not s.startswith("#") and len(partes) == 2 and partes[0].lower() in FOTOS_PRUEBA \
               and any((FOTOS / carp).exists() for carp in CARPETAS_JUBILADAS):
                quitadas += 1
                continue
            out.append(ln)
        if quitadas:
            ETIQ.write_text("\n".join(out) + "\n", encoding="utf-8")
            cambiados.append(f"etiquetas.txt: {quitadas} regla(s) de fotos de prueba eliminadas")

    if cambiados:
        for c in cambiados:
            print("+ " + c)
    else:
        print('Ya estaban jubiladas "Legado" y "Prueba Trimestre" (no toqué nada).')
    return 0


def revertir():
    claves = {c.lower() for c in JUBILAR}
    recuperadas = 0
    for ruta in [TRIM] + OTRAS + [ETIQ]:
        if not ruta.exists():
            continue
        ls = ruta.read_text(encoding="utf-8").splitlines()
        out = []
        for ln in ls:
            s = ln.strip()
            if s.startswith("# JUBILADO") and "|" in s:
                cuerpo = s.split(": ", 1)[1] if ": " in s else ""
                if _es_de_seccion(cuerpo, claves):
                    out.append(cuerpo)
                    recuperadas += 1
                    continue
            out.append(ln)
        if recuperadas and ruta == TRIM:
            out = [l for l in out if not _es_de_seccion(l.strip(), ["galeria"]) or l.strip().startswith("#")]
        ruta.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"+ Se devolvieron {recuperadas} línea(s)." if recuperadas else "No había nada jubilado que devolver.")
    if recuperadas:
        print("Ejecuta de nuevo la actualización para regenerar la galería.")
    return 0


def parche_webp(hechos):
    ruta = RAIZ / "assets" / "js" / "jfz.js"
    if not ruta.exists():
        print("AVISO (webp): no encontré assets/js/jfz.js en este proyecto. Avísale a Claude.")
        return
    s = ruta.read_text(encoding="utf-8")
    cambios = [
        ('f.replace(/\\.jpg$/i, "")', 'f.replace(/\\.(jpe?g|png|webp)$/i, "")'),
        ('/^IMG_(\\d+)\\.jpg$/i', '/^IMG_(\\d+)\\.(?:jpe?g|png|webp)$/i'),
    ]
    n = 0
    for viejo, nuevo in cambios:
        if viejo in s:
            s = s.replace(viejo, nuevo)
            n += 1
        elif nuevo not in s:
            print("AVISO (webp): no encontré el texto esperado en jfz.js (¿lo editaste?). Avísale a Claude.")
    if n:
        ruta.write_text(s, encoding="utf-8")
        hechos.append(f"Parche WebP aplicado ({n} cambios)")


def parche_galeria(hechos):
    ruta = RAIZ / "gallery.html"
    if not ruta.exists():
        print("AVISO (galería plus): no encontré gallery.html en este proyecto. Avísale a Claude.")
        return
    s = ruta.read_text(encoding="utf-8")
    pares = [
        ('<link href="assets/css/jfz.css" rel="stylesheet">', '<link href="assets/css/galeria-plus.css" rel="stylesheet">'),
        ('<script src="assets/js/jfz.js"></script>', '<script src="assets/js/galeria-plus.js"></script>'),
    ]
    n = 0
    for ancla, nueva in pares:
        if nueva in s:
            continue
        if ancla not in s:
            print("AVISO (galería): no encontré " + ancla + " en gallery.html. Avísale a Claude.")
            continue
        s = s.replace(ancla, ancla + "\n  " + nueva)
        n += 1
    if n:
        ruta.write_text(s, encoding="utf-8")
        hechos.append(f"Galería plus conectada ({n} cambios)")


LUPA = '<a class="jfz-buscabox" href="gallery.html#buscar" aria-label="Buscar fotos" title="Buscar fotos"><i class="bi bi-search"></i></a>'


def _reemplazo(ruta, viejo, nuevo, etiqueta, hechos):
    if not ruta.exists():
        print(f"AVISO ({etiqueta}): no encontré el archivo {ruta.name} en este proyecto. Avísale a Claude.")
        return
    s = ruta.read_text(encoding="utf-8")
    if nuevo in s:
        return
    if viejo not in s:
        print(f"AVISO ({etiqueta}): no encontré el texto esperado en {ruta.name} (¿lo editaste a mano?). Avísale a Claude.")
        return
    ruta.write_text(s.replace(viejo, nuevo, 1), encoding="utf-8")
    hechos.append(etiqueta)


def consolidar(hechos):
    pag = HERR / "index.html"
    if pag.exists():
        try:
            pag.unlink()
            hechos.append("herramientas/index.html eliminada (opcion inutil, oculta a pedido)")
        except OSError as e:
            hechos.append(f"No pude borrar herramientas/index.html: {e}")

    jfz = RAIZ / "assets" / "js" / "jfz.js"
    if not jfz.exists():
        print("AVISO: no encontré assets/js/jfz.js en este proyecto; salto los parches del sitio. Avísale a Claude.")
        return

    jfz_txt = jfz.read_text(encoding="utf-8")
    if 'herramientas/index.html' in jfz_txt:
        nav_linea = None
        for ln in jfz_txt.splitlines():
            if 'href="herramientas/index.html"' in ln and "<li>" in ln:
                nav_linea = ln
                break
        if nav_linea is not None:
            lineas = jfz_txt.splitlines(keepends=True)
            out = []
            for i, ln in enumerate(lineas):
                if 'href="herramientas/index.html"' in ln and "<li>" in ln:
                    continue
                out.append(ln)
            jfz_txt = "".join(out)
            import re as _re
            jfz_txt = _re.sub(r"['\"] \+\s*\n\s*['\"]</ul>", lambda m: m.group(0)[0] + " +\n      " + m.group(0)[-6:], jfz_txt)
            jfz.write_text(jfz_txt, encoding="utf-8")
            hechos.append("Menu: enlace «Herramientas» quitado (oculto a pedido)")

    s = jfz.read_text(encoding="utf-8")
    if LUPA in s:
        jfz.write_text(s.replace(LUPA, "", 1), encoding="utf-8")
        hechos.append("Header: lupa de búsqueda quitada (buscador oculto a pedido)")

    _reemplazo(RAIZ / "index.html",
               '<a href="gallery.html#buscar" class="btn-get-started">Ver galería completa</a>',
               '<a href="gallery.html" class="btn-get-started">Ver galería completa</a>',
               "index.html: «Ver galería completa» apunta a la galería normal", hechos)

    gal = RAIZ / "gallery.html"
    gtxt = gal.read_text(encoding="utf-8")
    if re.search(r'^\s*<div class="jfz-tabs-linea">.*herramientas/index\.html.*</div>\s*\n', gtxt, re.M):
        gtxt = re.sub(r'^\s*<div class="jfz-tabs-linea">.*herramientas/index\.html.*</div>\s*\n', "", gtxt, flags=re.M)
        gal.write_text(gtxt, encoding="utf-8")
        hechos.append("gallery.html: enlace a Herramientas quitado (oculto a pedido)")

    s = jfz.read_text(encoding="utf-8")
    if 'hash === "#buscar"' not in s:
        viejo_fin = 'window.addEventListener("hashchange", showTab);'
        nuevo_fin = (viejo_fin + "\n    if (location.hash === \"#buscar\") { setTimeout(function () { var bq = $(\"#jfz-q\"); if (bq) { try { bq.scrollIntoView({ behavior: \"smooth\", block: \"center\" }); } catch (e) {} bq.focus({ preventScroll: true }); } }, 80); }")
        if viejo_fin in s:
            jfz.write_text(s.replace(viejo_fin, nuevo_fin, 1), encoding="utf-8")
            hechos.append("jfz.js: el enlace #buscar hace scroll y enfoca el buscador")
        else:
            print('AVISO (#buscar): no encontré "hashchange" en jfz.js. Avísale a Claude.')

    s = jfz.read_text(encoding="utf-8")
    if "jfz-pie-herr" in s:
        s2 = re.sub(r"'<div class=\"jfz-pie-herr\">.*?</div>' \+ *\\n *", "", s)
        if s2 != s:
            jfz.write_text(s2, encoding="utf-8")
            hechos.append("Pie de pagina: enlace a Herramientas quitado (oculto a pedido)")

    css = RAIZ / "assets" / "css" / "jfz.css"
    extra_css = """
/* ---- botones consolidados (header + página de herramientas) ---- */
.jfz-buscabox { display: inline-flex; align-items: center; justify-content: center; width: 38px; height: 38px; margin-right: 6px; border-radius: 999px; border: 1px solid rgba(255,255,255,.35); color: #fff; text-decoration: none; transition: .2s; }
.jfz-buscabox:hover { background: var(--accent-color); border-color: var(--accent-color); }
.jfz-tabs-linea { display: flex; justify-content: flex-end; margin-bottom: 14px; }
.jfz-herr-enlace { font: 500 14px var(--nav-font); letter-spacing: .05em; color: rgba(255,255,255,.75); text-decoration: none; border: 1px solid rgba(255,255,255,.25); border-radius: 999px; padding: 6px 14px; }
.jfz-herr-enlace:hover { color: #fff; border-color: var(--accent-color); }
.jfz-herr-botones { display: flex; gap: 14px; flex-wrap: wrap; margin: 18px 0 6px; }
.jfz-pasos { margin: 12px 0 6px 22px; line-height: 1.9; }
.jfz-pasos li { margin-bottom: 6px; }
.jfz-herr-notas p { margin-bottom: 8px; }
.jfz-pie-herr { text-align: center; margin-top: 10px; }
.jfz-pie-herr a { color: rgba(255,255,255,.6); text-decoration: none; font-size: 14px; }
.jfz-pie-herr a:hover { color: var(--accent-color); }
"""
    scss = css.read_text(encoding="utf-8")
    if ".jfz-buscabox" not in scss:
        css.write_text(scss.rstrip() + "\n" + extra_css, encoding="utf-8")
        hechos.append("jfz.css: estilos de los paneles de herramientas")


BAT_DEFINITIVA = """@echo off
rem ============================================================
rem  "actualizacion definitive.bat" - EL BOTON UNICO de este sitio.
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set PY=py
where py >nul 2>nul || set PY=python

set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

%PY% actualizador.py %PASO_FINAL%

echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
"""

A_BORRAR = [
    "preparar_y_actualizar", "preparar fotos", "parche_webp", "parche_galeria",
    "migrar_legado", "marca agua", "jubilar_legado", "index", "consolidar_sitio",
    "actualizar todo", "mover_fotos_a_galeria", "actualizacion definitive 1",
    "actualizacion definitive 2", "actualizacion definitive 3",
]

def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("_", "").replace(" ", "").replace("-", "")


def limpiar_viejos(hechos):
    BORrables_ext = {".bat", ".cmd", ".ps1", ".py"}
    for ruta in sorted(RAIZ.rglob("*")):
        if not ruta.is_file():
            continue
        rel_parts = [p.lower() for p in ruta.relative_to(RAIZ).parts[:-1]]
        if ".git" in rel_parts or "node_modules" in rel_parts:
            continue
        stem = _norm(ruta.stem)
        carpeta = _norm(ruta.parent.name)
        if re.search(r"definitiv[ae][123]", stem):
            pass
        elif stem.startswith("actualizaciondefinitiv"):
            continue
        es_index_panel = (ruta.name.lower() == "index.html" and ruta.parent == HERR)
        ext_ok = ruta.suffix.lower() in BORrables_ext or es_index_panel
        if not ext_ok:
            continue
        if ruta.resolve() == Path(__file__).resolve():
            continue
        if stem in {"prepararfotos", "actualizargaleria", "actualizaciondefinitiva", "moverfotosagaleria", "pedido", "pedidops"}:
            continue
        if "legado" in stem or ("prueba" in stem and "trimestre" in stem) or "t9test" in stem:
            continue
        if stem == "marcaagua" and ruta.suffix.lower() == ".png":
            continue
        if re.search(r"definitiv[ae][123]", stem):
            try:
                ruta.unlink()
                hechos.append(f"Eliminado {ruta.relative_to(RAIZ)} (consolidado en actualizador.py)")
            except OSError as e:
                hechos.append(f"No pude borrar {ruta.relative_to(RAIZ)}: {e}")
            continue
        for patron in A_BORRAR:
            p = _norm(patron)
            if p == "index":
                coincide = es_index_panel or (stem == "index" and ruta.suffix.lower() in {".bat", ".cmd", ".ps1"})
            else:
                coincide = stem == p or stem.startswith(p)
            if coincide:
                try:
                    ruta.unlink()
                    hechos.append(f"Eliminado {ruta.relative_to(RAIZ)} (consolidado en actualizador.py)")
                except OSError as e:
                    hechos.append(f"No pude borrar {ruta.relative_to(RAIZ)}: {e}")
                break
    for ruta in sorted(RAIZ.iterdir()):
        if not ruta.is_file():
            continue
        n = ruta.name
        if (n.startswith("_c") or n.startswith("_trozo")) and n.endswith(".py"):
            try:
                ruta.unlink()
                hechos.append(f"Eliminado {n} (resto temporal de la consolidacion)")
            except OSError as e:
                hechos.append(f"No pude borrar {n}: {e}")
        elif n == "_ok.flag":
            try:
                ruta.unlink()
                hechos.append("Eliminado _ok.flag (resto temporal de la consolidacion)")
            except OSError as e:
                hechos.append(f"No pude borrar _ok.flag: {e}")
    if HERR.is_dir():
        marca_vieja = HERR / "marca_agua.png"
        marca_nueva = RAIZ / "marca_agua.png"
        if marca_vieja.exists() and not marca_nueva.exists():
            try:
                shutil.copy2(marca_vieja, marca_nueva)
                hechos.append("Copiado marca_agua.png a la raiz (recurso del paso 2)")
            except OSError as e:
                hechos.append(f"No pude copiar marca_agua.png a la raiz: {e}")
        try:
            shutil.rmtree(HERR)
            hechos.append("Eliminada la carpeta herramientas/ completa (a pedido; solo vivian copias viejas + marca_agua.png)")
        except OSError as e:
            hechos.append(f"No pude eliminar la carpeta herramientas/: {e}")


def crear_bat(hechos):
    bat = RAIZ / "actualizacion definitive.bat"
    bat.write_bytes(BAT_DEFINITIVA.replace("\n", "\r\n").encode("utf-8"))
    hechos.append('Creado "actualizacion definitive.bat" en la raiz (el boton unico: corre actualizador.py)')
    bat_viejo = HERR / "actualizacion_definitiva.bat"
    if bat_viejo.exists():
        try:
            bat_viejo.unlink()
            hechos.append("Eliminado herramientas/actualizacion_definitiva.bat (lo reemplaza el de la raiz)")
        except OSError as e:
            hechos.append(f"No pude borrar herramientas/actualizacion_definitiva.bat: {e}")


# ==================== PASO 2 CONSOLIDADO: conversion de fotos ====================
# CAMBIO: Calidad reducida de 80 a 70
CALIDAD = 70
LADO_MAXIMO = 1920
ANCHO_MARCA = 0.6
OPACIDAD = 0.5
POSICION = "centro"

POR_PROCESAR = RAIZ / "por-procesar"
SALIDA_P2 = RAIZ / "fotos"
MARCA_AGUA = RAIZ / "marca_agua.png"
if not MARCA_AGUA.exists():
    _marca_vieja = RAIZ / "herramientas" / "marca_agua.png"
    if _marca_vieja.exists():
        MARCA_AGUA = _marca_vieja
EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".heif"}
EXT_RAW = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng", ".rw2", ".orf", ".pef", ".raw"}
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def _normalizar_fecha(txt):
    f = str(txt or "").strip()[:10].replace("/", "-").replace(":", "-")
    if len(f) == 10 and f[4] == "-" and f[7] == "-":
        return f
    return None


def _fecha_cr2_muy_grande(origen):
    try:
        datos = origen.read_bytes()
        if len(datos) < 16:
            return None
        endian = "<" if datos[6:8] == b"II" else ">"
        u16 = lambda b, o: int.from_bytes(b[o:o + 2], endian)
        u32 = lambda b, o: int.from_bytes(b[o:o + 4], endian)

        def leer_ifd(bloque, base):
            try:
                n = u16(bloque, 0)
                if n > 600 or len(bloque) < 2 + 12 * n:
                    return None
                salida = {}
                for i in range(n):
                    e = 2 + 12 * i
                    tag, typ, cnt = u16(bloque, e), u16(bloque, e + 2), u32(bloque, e + 4)
                    if typ == 2:
                        tam = max(cnt, 1)
                        if tam <= 4:
                            txt = bloque[e + 8:e + 8 + tam]
                        elif 4 + tam <= len(bloque):
                            off = u32(bloque, e + 8)
                            if not (off < base or off - base + tam <= len(bloque)):
                                continue
                            txt = bloque[off - base:off - base + tam]
                        else:
                            continue
                        v = txt.split(b"\x00")[0].decode("ascii", "ignore").strip()
                        if v:
                            salida[tag] = v
                    elif tag in (0x8769, 0xA005):
                        salida[tag] = u32(bloque, e + 8)
                nxt = u32(bloque, 2 + 12 * n) if len(bloque) >= 2 + 12 * n + 4 else 0
                return salida, nxt
            except Exception:
                return None

        cola = [int.from_bytes(datos[8:12], endian)]
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
            for tag in (36867, 36868, 306):
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
    extra = {"exif": exif} if exif else {}
    try:
        # CAMBIO: Calidad reducida de 95 a 70
        im.save(destino_jpg, "JPEG", quality=70, **extra)
    except (ValueError, TypeError):
        im.save(destino_jpg, "JPEG", quality=70)


def revelar_raw(origen, destino_jpg):
    import io
    fecha = None
    jpg = None
    if rawpy is not None:
        try:
            with rawpy.imread(str(origen)) as r:
                jpg = r.postprocess(use_auto_wb=True)
                try:
                    fecha = _normalizar_fecha(getattr(r.other, "capture_time", ""))
                except Exception:
                    fecha = None
        except Exception as e:
            print(f"    AVISO: rawpy no pudo revelar {origen.name} ({e}); pruebo la via alternativa.")
            
    if jpg is None:
        try:
            with Image.open(origen) as im:
                exif = im.getexif()
                try:
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
                # CAMBIO: Calidad reducida de 95 a 70 para el temporal
                im.save(buf, "JPEG", quality=70)
                jpg = buf.getvalue()
        except Exception as e:
            print(f"    AVISO: Pillow tampoco abrio {origen.name} ({type(e).__name__}: {e}).")
            if origen.suffix.lower() == ".cr2":
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
        exif = im.getexif()
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        if 274 in exif:
            del exif[274]
        im = im.convert("RGB")
        if LADO_MAXIMO:
            im.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
        if marca is not None:
            im = poner_marca(im, marca)
        extra = {"icc_profile": icc} if icc else {}
        # CAMBIO: Aquí ya se usaba la variable CALIDAD, que ahora es 70
        im.save(destino, "WEBP", quality=CALIDAD, method=6, exif=exif, **extra)


def registrar_fecha(carpeta, nombre_sin_ext, fecha):
    txt = RAIZ / "fotos" / "fechas.txt"
    linea = f"{carpeta} | {nombre_sin_ext} | {fecha}\n"
    existentes = txt.read_text(encoding="utf-8").splitlines() if txt.exists() else []
    for l in existentes:
        p = [x.strip() for x in l.split("|")]
        if len(p) == 3 and p[0].lower() == carpeta.lower() and p[1].lower() == nombre_sin_ext.lower():
            return
    with txt.open("a", encoding="utf-8") as f:
        f.write(linea)


GALERIA = SALIDA_P2 / "galeria"


def _nombre_webp(stem):
    return stem.strip().replace(" ", "-").lower()


def _nombre_foto(stem):
    return stem.strip().replace(" ", "-")


def _nombre_unico(stem):
    base = _nombre_foto(stem)
    ideal = GALERIA / f"{base}.webp"
    if not ideal.exists():
        return ideal
    canon = _nombre_webp(stem)
    for p in GALERIA.iterdir():
        if _nombre_webp(p.stem) == canon:
            return p
    i = 1
    destino = GALERIA / f"{base}_{i}.webp"
    while destino.exists():
        i += 1
        destino = GALERIA / f"{base}_{i}.webp"
    return destino


def _existe_en_galeria(canon):
    for p in GALERIA.iterdir():
        if p.is_file() and p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png") \
                and _nombre_webp(p.stem) == canon:
            return True
    return False


# =========================================================================
# FUNCIÓN CORREGIDA: convertir_todas con barra de progreso integrada
# =========================================================================
def convertir_todas():
    POR_PROCESAR.mkdir(exist_ok=True)
    GALERIA.mkdir(parents=True, exist_ok=True)
    
    grupos = {}
    for p in sorted(POR_PROCESAR.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in EXTENSIONES and ext not in EXT_RAW:
            continue
        rel = p.relative_to(POR_PROCESAR)
        clave = rel.parts[0] if len(rel.parts) > 1 else "_sueltas"
        grupos.setdefault(clave, []).append(p)
        
    if not grupos:
        print("No hay fotos dentro de 'por-procesar'. Mete ahi tus fotos terminadas")
        print("(sueltas o en carpetas, ej. por-procesar/t4/) y vuelve a ejecutar.")
        return 1
        
    marca = None
    if MARCA_AGUA.exists():
        marca = Image.open(MARCA_AGUA).convert("RGBA")
        caja = marca.getchannel("A").getbbox()
        if caja:
            marca = marca.crop(caja)
        print(f"Marca de agua: {marca.width}x{marca.height} px, una sola, en el {POSICION}.")
        if marca.width > 1500 or marca.height > 1500:
            print("AVISO: tu marca_agua.png es enorme. Debe ser UN solo logo, no una imagen con el logo repetido.")
    else:
        print("!! No encontre marca_agua.png (raiz): las fotos saldrian SIN marca de agua.")
        print("!! Tu repositorio es publico: cualquiera podria descargarlas limpias.")
        try:
            resp = input("Escribe SI para continuar de todos modos, o pulsa Enter para cancelar: ").strip().upper()
        except EOFError:
            resp = ""
        if resp != "SI":
            print("Cancelado. Pon tu marca de agua (PNG transparente) en la raiz como marca_agua.png y repite.")
            return 1
            
    GALERIA.mkdir(parents=True, exist_ok=True)
    total = 0
    
    for clave in sorted(grupos):
        archivos = grupos[clave]
        nuevas = 0
        temporales = []
        fallan_raw = []
        
        # --- AQUÍ SE APLICA LA BARRA DE PROGRESO ---
        barra = _barra_progreso(len(archivos), desc=f"Procesando carpeta '{clave}'")
        for idx in barra:
            f = archivos[idx]
            origen = f
            canon = _nombre_webp(f.stem)
            if _existe_en_galeria(canon):
                continue
            try:
                if f.suffix.lower() in EXT_RAW:
                    if rawpy is None:
                        print(f"  AVISO: {f.name} es RAW y te falta la libreria. Instala: py -m pip install rawpy")
                        continue
                    tmp = RAIZ / "__tmp__" / f"{clave}_{f.stem}.jpg"
                    tmp.parent.mkdir(exist_ok=True)
                    fecha_raw = revelar_raw(f, tmp)
                    if not tmp.exists():
                        fallan_raw.append(f.name)
                        continue
                    origen = tmp
                    temporales.append(tmp)
                    if fecha_raw:
                        registrar_fecha("galeria", f.stem, fecha_raw)
                else:
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
                
        # Cerrar la barra de progreso al terminar la carpeta
        try:
            barra.close()
        except Exception:
            pass
            
        for tmp in temporales:
            try:
                tmp.unlink()
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
# =========================================================================


EXT_FOTO_P2 = EXTENSIONES | EXT_RAW


def _claves_procesables():
    claves_normal, claves_guion, webps_locales = set(), set(), set()
    if POR_PROCESAR.is_dir():
        for p in POR_PROCESAR.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXT_FOTO_P2:
                stem = p.stem.strip()
                claves_normal.add(stem.lower())
                claves_guion.add(stem.replace(" ", "-").lower())
                if p.suffix.lower() == ".webp":
                    webps_locales.add(stem.replace(" ", "-").lower())
    return claves_normal, claves_guion, webps_locales


def _pertenece_a_procesar(nombre_sin_ext, claves_normal, claves_guion):
    n = nombre_sin_ext.lower()
    if n in claves_normal or n in claves_guion:
        return True
    base, _, sufijo = n.rpartition("_")
    return bool(sufijo.isdigit()) and base in claves_normal


def _igualar_mayusculas(stem):
    canon = _nombre_webp(stem)
    if POR_PROCESAR.is_dir():
        for p in POR_PROCESAR.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXT_FOTO_P2 and _nombre_webp(p.stem) == canon:
                return p.stem.replace(" ", "-")
    return canon


# =========================================================================
# FUNCIÓN ACTUALIZADA: igualar_galeria_a_por_procesar CON BARRA DE PROGRESO
# =========================================================================
def igualar_galeria_a_por_procesar():
    renombradas, borradas, faltantes = [], [], []
    claves_normal, claves_guion, webps_locales = _claves_procesables()
    if not claves_normal or not GALERIA.is_dir():
        return renombradas, borradas, faltantes

    presentes = {p.name for p in GALERIA.iterdir() if p.is_file()}
    presentes_norm = {p.lower() for p in presentes}
    deseados = set()
    for canon in sorted(claves_guion):
        destino = f"{_igualar_mayusculas(canon)}.webp"
        deseados.add(destino)
        if destino not in presentes and destino.lower() not in presentes_norm:
            faltantes.append(destino)

    a_borrar, a_renombrar = [], []
    for p in sorted(GALERIA.iterdir()):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in (".webp", ".jpg", ".jpeg", ".png"):
            continue
        if not _pertenece_a_procesar(p.stem, claves_normal, claves_guion):
            a_borrar.append(p)
            continue
        if ext == ".webp":
            ideal = f"{_igualar_mayusculas(p.stem)}.webp"
            if p.name != ideal:
                if _nombre_webp(ideal[:-5]) != _nombre_webp(p.stem):
                    a_borrar.append(p)
                elif (GALERIA / ideal).exists():
                    a_borrar.append(p)
                else:
                    a_renombrar.append((p, GALERIA / ideal))
            elif p.name.lower() in deseados and p.name not in deseados:
                a_renombrar.append((p, GALERIA / next(d for d in deseados if d.lower() == p.name.lower())))
        else:
            a_borrar.append(p)

    # --- BARRA DE PROGRESO PARA RENOMBRAR ---
    if a_renombrar:
        print(f"\nSincronizando galería: {len(a_renombrar)} archivos por renombrar...")
        barra_renombrar = _barra_progreso(len(a_renombrar), desc="Renombrando")
        for idx in barra_renombrar:
            origen, destino = a_renombrar[idx]
            try:
                if destino.exists():
                    if origen.stat().st_size >= destino.stat().st_size:
                        destino.unlink()
                        origen.rename(destino)
                        renombradas.append(f"{origen.name} -> {destino.name}")
                    else:
                        a_borrar.append(origen)
                else:
                    origen.rename(destino)
                    renombradas.append(f"{origen.name} -> {destino.name}")
            except OSError as e:
                print(f"AVISO (espejo): no pude renombrar {origen.name}: {e}")
        try:
            barra_renombrar.close()
        except Exception:
            pass

    # --- BARRA DE PROGRESO PARA ELIMINAR ---
    if a_borrar:
        print(f"\nLimpiando galería: {len(a_borrar)} archivos por eliminar...")
        barra_borrar = _barra_progreso(len(a_borrar), desc="Eliminando")
        for idx in barra_borrar:
            p = a_borrar[idx]
            try:
                p.unlink()
                borradas.append(p.name)
            except OSError as e:
                print(f"AVISO (espejo): no pude borrar {p.name}: {e}")
        try:
            barra_borrar.close()
        except Exception:
            pass

    presentes = {p.name for p in GALERIA.iterdir() if p.is_file() and p.suffix.lower() == ".webp"}
    sobran = sorted(p for p in presentes
                    if p not in deseados and p.lower() not in {d.lower() for d in deseados})
    if sobran:
        print(f"\nVerificación final: {len(sobran)} archivos adicionales por eliminar...")
        barra_final = _barra_progreso(len(sobran), desc="Verificando")
        for idx in barra_final:
            nombre = sobran[idx]
            try:
                (GALERIA / nombre).unlink()
                borradas.append(nombre)
            except OSError as e:
                print(f"AVISO (espejo): no pude borrar {nombre}: {e}")
        try:
            barra_final.close()
        except Exception:
            pass
        
    return renombradas, borradas, faltantes
# =========================================================================


def fecha_exif(ruta):
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
    stems = [Path(f).stem for f in fotos]
    resultado = {}
    for selector, lista in reglas:
        ext = [s.strip() for s in selector.replace(" a ", "|").split("|")]
        try:
            ini, fin = stems.index(ext[0]), stems.index(ext[-1])
        except ValueError:
            continue
        for i in range(min(ini, fin), max(ini, fin) + 1):
            resultado[fotos[i]] = list(lista)
    return {f: v for f, v in resultado.items() if v}


def generar_fotos_js():
    reglas = leer_fechas_manuales()
    etiquetas_reglas = leer_etiquetas()
    secciones = []
    for linea in (FOTOS / "trimestres.txt").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "|" not in linea:
            continue
        carpeta, titulo = [x.strip() for x in linea.split("|", 1)]
        reales = {d.name.lower(): d.name for d in FOTOS.iterdir() if d.is_dir()}
        carpeta = reales.get(carpeta.lower(), carpeta)
        ruta = FOTOS / carpeta
        ruta.mkdir(exist_ok=True)
        fotos = sorted(p.name for p in ruta.iterdir() if p.suffix.lower() in EXT_FOTOS)
        seccion = {"id": carpeta, "titulo": titulo, "carpeta": carpeta, "fotos": fotos}
        fechas = fechas_de_seccion(carpeta, fotos, ruta, reglas)
        if fechas:
            seccion["fechas"] = fechas
        ets = etiquetas_de_seccion(fotos, ruta, etiquetas_reglas)
        ets = {f: v for f, v in ets.items() if v}
        if ets:
            seccion["etiquetas"] = ets
            seccion["todas_etiquetas"] = sorted({e for v in ets.values() for e in v})
        secciones.append(seccion)
        print(f"{titulo}: {len(fotos)} fotos ({len(fechas)} con fecha, {len(ets)} con etiquetas)")

    (RAIZ / "assets/js/fotos.js").write_text(
        "/* ARCHIVO GENERADO por actualizador.py - no lo edites a mano */\n"
        "window.JFZ_FOTOS = " + json.dumps(secciones, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    if Image is None:
        print("AVISO: no tienes Pillow instalado, no pude leer fechas dentro de las fotos (py -m pip install Pillow).")
    print("Listo: assets/js/fotos.js actualizado.")


def paso_principal():
    paso_final = 3
    for arg in sys.argv[1:]:
        if arg in {"1", "2", "3"}:
            paso_final = int(arg)

    if "--revertir" in sys.argv:
        rc = revertir()
        generar_fotos_js()
        return rc

    print("=== ACTUALIZADOR: unico script del flujo (orden + parches + fotos + galeria) ===")
    if not (RAIZ / "marca_agua.png").exists() and not (HERR / "marca_agua.png").exists():
        print(MARCA_AGUIO.replace("\n", " "))

    print("\n--- A) Ordenando la carpeta fotos/ hacia fotos/galeria ---")
    mov, av = ordenar_fotos()
    for m in mov:
        print("+ Foto ordenada a la galería general: " + m)
    for a in av:
        print("AVISO: " + a)
    if not mov and not av:
        print("fotos/ ya estaba ordenada: todas las fotos viven en fotos/galeria/.")
    if "--jubilar-legacy" in sys.argv:
        print("\n--- A2) Jubilando secciones antiguas (fotos -> fotos/galeria) ---")
        mover_fotos_jubiladas()
        jubilar()
    else:
        print("\n--- A2) Legado / Prueba Trimestre: SIN TOCAR (codigo de jubilacion quitado del boton) ---")

    print("\n--- B) Parches y consolidación del sitio ---")
    hechos = []
    parche_webp(hechos)
    parche_galeria(hechos)
    consolidar(hechos)
    for h in hechos:
        print("+ " + h)
    if not hechos:
        print("Sitio: los parches ya estaban aplicados (no hice nada).")

    print("\n--- C) Botón único ---")
    hechos_bat = []
    crear_bat(hechos_bat)
    for h in hechos_bat:
        print("+ " + h)

    if paso_final < 2:
        print("\n(Solo se pidio el paso 1: no conversion. Ejecuta el boton sin numero para el flujo completo.)")
        return 0

    print("\n--- D) Convirtiendo por-procesar/ a WebP (con marca de agua) ---")
    if Image is None:
        print("AVISO: sin Pillow no puedo convertir fotos. Instala: py -m pip install Pillow")
        rc_conv = 2
    else:
        rc_conv = convertir_todas()
    if rc_conv == 1:
        print("(No habia fotos nuevas en por-procesar: la galeria sigue igual.)")

    print("\n--- D2) Igualando fotos/galeria a por-procesar (espejo exacto en .webp) ---")
    renom, borr, falt = igualar_galeria_a_por_procesar()
    if not (POR_PROCESAR.is_dir() and any(p.is_file() and p.suffix.lower() in EXT_FOTO_P2
                                          for p in POR_PROCESAR.rglob("*"))):
        print("por-procesar esta vacio: NO se borra nada (tus fotos de la galeria quedan intactas).")
    else:
        for r in renom:
            print("+ Renombrada para igualar el numero: " + r)
        for b in borr:
            print("- Borrada de la galeria (no esta en por-procesar): " + b)
        for f in falt:
            print("AVISO: no pude tener " + f + " en la galeria; revisa esa foto en por-procesar.")
        total_webp = sum(1 for p in GALERIA.iterdir() if p.is_file() and p.suffix.lower() == ".webp")
        print(f"Galeria sincronizada: {total_webp} archivos .webp = la misma cantidad/nombres que por-procesar.")

    print("\n--- E) Regenerando assets/js/fotos.js ---")
    rc = 0
    try:
        generar_fotos_js()
    except BaseException as e:
        print("AVISO: fallo la generacion de fotos.js:", e)
        rc = 1

    print("\n--- F) Limpieza de archivos viejos ---")
    hechos_lim = []
    limpiar_viejos(hechos_lim)
    for h in hechos_lim:
        print("+ " + h)
    if not hechos_lim:
        print("Limpieza: no quedaba ningún archivo viejo por eliminar.")
    for viejo_boton in ("preparar_y_actualizar.bat", "actualizar todo.bat"):
        for ruta_boton in (HERR / viejo_boton, RAIZ / viejo_boton):
            if ruta_boton.exists():
                try:
                    ruta_boton.unlink()
                    print(f"+ Eliminado el boton heredado {ruta_boton.name} (ahora existe actualizacion definitive.bat)")
                except OSError:
                    pass

    print()
    if "--jubilar-legacy" in sys.argv:
        print('Listo: "Legado" y "Prueba Trimestre" dejaron de existir en la galería.')
    else:
        print('Listo: las categorías "Legado" y "Prueba Trimestre" quedaron SIN tocar.')
    print('Para el dia a dia usa "actualizacion definitive.bat" (doble clic, en la raiz del proyecto).')
    return rc


if __name__ == "__main__":
    raise SystemExit(paso_principal())