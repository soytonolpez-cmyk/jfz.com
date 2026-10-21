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
     por-procesar/, todos en formato .webp:
       - cada foto de por-procesar/ (ej. IMG_6001.jpg o t4/IMG_6001.CR2) debe
         terminar existiendo en fotos/galeria/ como IMG_6001.webp; si no se
         pudo convertir, se avisa en pantalla;
       - cualquier archivo de fotos/galeria/ que NO corresponda a una foto de
         por-procesar/ se elimina (sobrantes de otras extensiones y .webp con
         sufijo _1, _2... duplicados);
       - los nombres se igualan: si por-procesar tiene IMG_6001.CR2 y la galeria
         tenia ese numero guardado como IMG_6001_1.webp, se renombra a
         IMG_6001.webp.
     Proteccion: si por-procesar esta VACIO no se borra nada (asi tus fotos no
     dependen de que la carpeta local exista; es la unica salvaguarda deliberada).
  E) REGENERA assets/js/fotos.js (los numeros/nombres/cantidad de webp que ve
     el sitio son exactamente los de fotos/galeria/, o sea los de por-procesar/).
  F) LIMPIEZA: elimina los viejos "actualizacion definitiva 1/2/3.py", toda la
     carpeta herramientas/ y demas archivos consolidados (guarda marca_agua.png
     en la raiz antes de borrarla).

FLUJO DIARIO: mete tus fotos en por-procesar\\ -> doble clic a
"actualizacion definitive.bat" -> GitHub Desktop: Commit to main + Push origin.
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
except ImportError:
    pillow_heif = None
else:
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass

# RAIZ = carpeta del proyecto (este script vive en la raiz).
RAIZ = Path(__file__).resolve().parent
HERR = RAIZ / "herramientas"   # vieja carpeta de herramientas (se elimina en la limpieza)


import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
HERR = RAIZ / "herramientas"
FOTOS = RAIZ / "fotos"
TRIM = RAIZ / "fotos" / "trimestres.txt"
OTRAS = [RAIZ / "fotos" / "fechas.txt"]
ETIQ = RAIZ / "fotos" / "etiquetas.txt"

# Secciones que dejan de existir en la galeria (se comparan en minusculas).
# Incluye todas las variantes reales con las que aparecen en trimestres.txt:
# legado/Legado y t9test/"Prueba Trimestre"/prueba-trimestre.
JUBILAR = ["legado", "Legado", "t9test", "prueba trimestre", "prueba-trimestre"]
# Fotos de prueba cuya etiqueta conviene quitar al jubilar la seccion
FOTOS_PRUEBA = ["img_9001", "img_9002"]
# Carpetas jubiladas donde pueden estar esas fotos de prueba
CARPETAS_JUBILADAS = ["legado", "t9test"]
# Carpeta general de la galeria: aca llegan las fotos sacadas de Legado/Prueba
DESTINO_GALERIA = FOTOS / "galeria"
EXT_FOTOS = (".jpg", ".jpeg", ".png", ".webp")
# Tambien se mueven (y convierten a JPG) los formatos que el navegador no muestra.
EXT_EXTRA = (".heic", ".heif", ".tif", ".tiff")

MARCA_AGUIO = """AVISO: no encontre marca_agua.png (quedo duplicado en la raiz y en
herramientas/ durante la transicion). El paso 2 avisa si falta; para convertir
necesitas ahi tu logo PNG transparente."""


def _normalizar(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _es_carjeta_jubilada(nombre_carpeta):
    """Reconoce cualquier variante real de las carpetas jubiladas:
    legado/Legado/LEGADO, 'prueba trimestre', 't9test', 'prueba-trimestre', etc."""
    n = _normalizar(nombre_carpeta)
    return ("legado" in n) or ("prueba" in n and "trimestre" in n) or n == "t9test"


# Extensiones de imagen que reconoce el navegador (para renombrar al mover).
EXT_NAVEGADOR = (".jpg", ".jpeg", ".png", ".webp")


def _renombrar_para_navegador(nombre):
    """Si la foto jubilada viene en un formato que el navegador no muestra
    (HEIC de iPhone, TIFF...), se convierte al moverla a fotos/galeria/ con
    extension .jpg. Si ya es jpg/png/webp, se deja igual."""
    p = Path(nombre)
    if p.suffix.lower() in EXT_NAVEGADOR:
        return nombre
    try:
        from PIL import Image  # lectura suave: si falta Pillow, se mueve igual
    except ImportError:
        return nombre
    try:
        import pillow_heif     # HEIC/HEIF de iPhone (opcional)
    except ImportError:
        pillow_heif = None
    if pillow_heif is not None:
        try:
            pillow_heif.register_heif_opener()
        except Exception:
            pass
    try:
        with Image.open(p) as im:
            im.verify()        # solo comprobar que es una imagen legible
    except Exception:
        return nombre          # no se puede leer: se mueve tal cual
    return p.stem + ".jpg"


def _convertir_a_jpg(origen, destino):
    """Revela/redimensiona una foto que el navegador no muestra (HEIC, TIFF...)
    y la guarda como JPG en destino. Devuelve True si lo logr6."""
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
            im.save(destino, "JPEG", quality=85)
        return True
    except Exception:
        return False


LADO_MAXIMO_FOTO = 1920  # mismo tope que preparar_fotos.py al convertir jubiladas


def _destino_libre(nombre):
    """fotos/galeria/<nombre>; si ya existe uno, agrega _1, _2... detras."""
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
    """Mueve un archivo a fotos/galeria/ (renombrando si hay choque o si el
    navegador no muestra el formato). Devuelve el texto del registro o None."""
    import shutil
    destino = _destino_libre(destino_base or origen.name)
    try:
        if destino.suffix.lower() == ".jpg" and origen.suffix.lower() not in EXT_FOTOS:
            # HEIC/TIFF: el navegador no lo muestra -> se convierte a JPG
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
    """Recoge las fotos que esten SUELTAS dentro de fotos/ (y subcarpetas no
    jubiladas, como t4/) y las mueve a la carpeta general fotos/galeria/.
    Asi la galeria siempre muestra TODO: es la unica seccion que existe ahora.
    Idempotente: si no queda nada suelto, no hace nada."""
    movidas, avisos = [], []
    if not FOTOS.is_dir():
        return movidas, avisos
    DESTINO_GALERIA.mkdir(exist_ok=True)
    # 1) archivos sueltos directamente en fotos/ (cualquier extension de foto)
    for p in sorted(FOTOS.iterdir()):
        if not p.is_file() or p.suffix.lower() not in (EXT_FOTOS + EXT_EXTRA):
            continue
        res = _mover_a_galeria(p, None)
        if res and res.startswith("__ERROR__"):
            avisos.append(f"No pude mover {p.name}: {res[10:]}")
        elif res:
            movidas.append(res)
    # 2) fotos dentro de subcarpetas que NO sean galeria ni estar jubiladas
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
        # eliminar la subcarpeta si quedo vacia (solo carpetas, conservo los .txt)
        try:
            if sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()
        except OSError:
            pass
    return movidas, avisos


def mover_fotos_jubiladas():
    """Mueve las fotos de galeria>legado y galeria>prueba trimestre hacia
    la carpeta general fotos/galeria/. Idempotente: si no queda nada, no hace nada."""
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


# ---------------------------------------------------------------- jubilacion --
def _es_de_seccion(linea, claves):
    partes = [x.strip() for x in linea.split("|")]
    return bool(partes) and partes[0].lower() in {c.lower() for c in claves}


def jubilar():
    """Comenta las lineas de las secciones jubiladas (no mueve ni borra fotos)."""
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
        # Si nadie activo "galeria" como seccion propia, se agrega al final para
        # que las fotos jubiladas que ahora viven en fotos/galeria/ se vean.
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

    # etiquetas.txt: quitar SOLO las lineas de las fotos de prueba (si existen);
    # las demas etiquetas (moto/casco/caras) se conservan tal cual.
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
    """Descomenta las lineas JUBILADAS de las secciones (devuelve Legado/Prueba)."""
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
        # Si la seccion «galeria» es la que agrego esta herramienta (linea sin
        # tocar), al devolver Legado/Prueba se quita para no duplicar fotos.
        if recuperadas and ruta == TRIM:
            out = [l for l in out if not _es_de_seccion(l.strip(), ["galeria"]) or l.strip().startswith("#")]
        ruta.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"+ Se devolvieron {recuperadas} línea(s)." if recuperadas else "No había nada jubilado que devolver.")
    if recuperadas:
        print("Ejecuta de nuevo la actualización para regenerar la galería.")
    return 0


# --------------------------------------------------------------- parches (B) --
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


# (Pagina herramientas/index.html ELIMINADA a pedido: era una opcion inutil y quedo
# oculta del sitio. Antes vivia en la constante PAGINA_HERRAMIENTAS; ahora ni se
# genera ni se enlaza, y la carpeta herramientas/ se borra en limpiar_viejos.)


def consolidar(hechos):
    """Equivalente a consolidar_sitio.py (parches del sitio; sin pagina de herramientas)."""
    # 1) La pagina de herramientas quedo OCULTA a pedido (pagina inutil): ya no se
    #    regenera herramientas/index.html; la carpeta herramientas/ se elimina en la
    #    limpieza (ver limpiar_viejos). Si existiera un panel viejo, se quita.
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

    # 2) Menu: el enlace "Herramientas" queda OCULTO a pedido (pagina inutil);
    #    si una version anterior del boton lo hubiera agregado, se quita ahora.
    jfz_txt = jfz.read_text(encoding="utf-8")
    if 'herramientas/index.html' in jfz_txt:
        nav_linea = None
        for ln in jfz_txt.splitlines():
            if 'href="herramientas/index.html"' in ln and "<li>" in ln:
                nav_linea = ln
                break
        if nav_linea is not None:
            # quitar la linea del <li> y tambien el "+ " colgante de la linea anterior
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

    # la lupa ya NO va en el header: si estaba puesta, se quita (buscador oculto a pedido)
    s = jfz.read_text(encoding="utf-8")
    if LUPA in s:
        jfz.write_text(s.replace(LUPA, "", 1), encoding="utf-8")
        hechos.append("Header: lupa de búsqueda quitada (buscador oculto a pedido)")

    # 3) index.html: "Ver galería completa" apunta a la galeria normal
    _reemplazo(RAIZ / "index.html",
               '<a href="gallery.html#buscar" class="btn-get-started">Ver galería completa</a>',
               '<a href="gallery.html" class="btn-get-started">Ver galería completa</a>',
               "index.html: «Ver galería completa» apunta a la galería normal", hechos)

    # 4) gallery.html: el enlace a Herramientas queda OCULTO a pedido (pagina
    #    inutil); si una version anterior lo hubiera agregado activo, se quita.
    gal = RAIZ / "gallery.html"
    gtxt = gal.read_text(encoding="utf-8")
    if re.search(r'^\s*<div class="jfz-tabs-linea">.*herramientas/index\.html.*</div>\s*\n', gtxt, re.M):
        gtxt = re.sub(r'^\s*<div class="jfz-tabs-linea">.*herramientas/index\.html.*</div>\s*\n', "", gtxt, flags=re.M)
        gal.write_text(gtxt, encoding="utf-8")
        hechos.append("gallery.html: enlace a Herramientas quitado (oculto a pedido)")

    # 5) jfz.js: llegar con #buscar enfoca el buscador
    s = jfz.read_text(encoding="utf-8")
    if 'hash === "#buscar"' not in s:
        viejo_fin = 'window.addEventListener("hashchange", showTab);'
        nuevo_fin = (viejo_fin + "\n    if (location.hash === \"#buscar\") { setTimeout(function () { var bq = $(\"#jfz-q\"); if (bq) { try { bq.scrollIntoView({ behavior: \"smooth\", block: \"center\" }); } catch (e) {} bq.focus({ preventScroll: true }); } }, 80); }")
        if viejo_fin in s:
            jfz.write_text(s.replace(viejo_fin, nuevo_fin, 1), encoding="utf-8")
            hechos.append("jfz.js: el enlace #buscar hace scroll y enfoca el buscador")
        else:
            print('AVISO (#buscar): no encontré "hashchange" en jfz.js. Avísale a Claude.')

    # 6) Pie de pagina: el enlace a Herramientas queda OCULTO a pedido; si una
    #    version anterior lo hubiera agregado, se quita ahora.
    s = jfz.read_text(encoding="utf-8")
    if "jfz-pie-herr" in s:
        s2 = re.sub(r"'<div class=\"jfz-pie-herr\">.*?</div>' \+ *\\n *", "", s)
        if s2 != s:
            jfz.write_text(s2, encoding="utf-8")
            hechos.append("Pie de pagina: enlace a Herramientas quitado (oculto a pedido)")

    # 7) jfz.css: estilos de los paneles de herramientas
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
rem  Vive en la RAIZ del proyecto (junto a las fotos y las paginas).
rem  Doble clic y hace TODO el flujo automatico de una sola vez:
rem    python actualizador.py  ->  ordena fotos\\, aplica los parches
rem    del sitio, convierte por-procesar\\ a WebP con marca de agua,
rem    deja fotos\\galeria\\ como ESPEJO EXACTO de por-procesar\\
rem    (los mismos numeros, nombres y cantidad de archivos .webp)
rem    y regenera assets\\js\\fotos.js
rem  Despues: GitHub Desktop -> Commit to main -> Push origin.
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizacion definitive.bat" 1  -> solo orden + parches
rem    "actualizacion definitive.bat" 2  -> hasta convertir/espejar fotos
rem    "actualizacion definitive.bat" 3  -> todo el flujo (por defecto)
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem --- elige el interprete de Python (py = el lanzador de Windows; si no, python) ---
set PY=py
where py >nul 2>nul || set PY=python

rem --- paso final por defecto: 3 = todo el flujo; acepta un numero como argumento ---
set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

%PY% actualizador.py %PASO_FINAL%

echo.
echo Cuando termine: abre GitHub Desktop, escribe un titulo y pulsa "Commit to main" y luego "Push origin".
pause
"""


# Archivos que la "actualización definitiva" debe eliminar del proyecto.
# Cualquier variante de nombre/tildes/espaceado que aparezca en el repo se borra,
# EXCEPTO las piezas que quedan por diseño: preparar_fotos.py, marca_agua.png,
# actualizar_galeria.py y pedido.ps1 (ver docstring arriba).
A_BORRAR = [
    "preparar_y_actualizar",   # .bat/.cmd/.ps1/.py
    "preparar fotos",          # variantes con espacio del viejo lote
    "parche_webp",             # .py/.bat (y su carpeta "pedido/parche_webp*" si existiera)
    "parche_galeria",
    "migrar_legado",
    "marca agua",              # variantes con espacio (NO toca marca_agua.png)
    "jubilar_legado",
    "index",                   # paneles viejos: SOLO herramientas/index.html (oculto a
                               # pedido por inutil) y cualquier "index.bat" heredado
    "consolidar_sitio",
    "actualizar todo",         # .bat/.cmd/.ps1
    "mover_fotos_a_galeria",   # incluido en el flujo del boton unico (el paso 2 ya guarda en galeria)
    "actualizacion definitive 1",  # los tres pasos quedaron consolidados en actualizador.py
    "actualizacion definitive 2",
    "actualizacion definitive 3",
]

def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("_", "").replace(" ", "").replace("-", "")


def limpiar_viejos(hechos):
    """Elimina los archivos consolidados que todavia existan en el repo."""
    BORrables_ext = {".bat", ".cmd", ".ps1", ".py"}
    for ruta in sorted(RAIZ.rglob("*")):
        if not ruta.is_file():
            continue
        rel_parts = [p.lower() for p in ruta.relative_to(RAIZ).parts[:-1]]
        if ".git" in rel_parts or "node_modules" in rel_parts:
            continue
        stem = _norm(ruta.stem)
        carpeta = _norm(ruta.parent.name)
        # Los VIEJOS "actualizacion definitive 1/2/3.py" ahora SI se borran:
        # quedaron consolidados en este unico script (actualizador.py). La tilde
        # de "actualización" se normaliza aqui para detectar tambien esa variante.
        if re.search(r"definitiv[ae][123]", stem):
            pass                                # es uno de los tres pasos viejos: puede borrarse
        elif stem.startswith("actualizaciondefinitiv"):
            continue                            # "actualizacion definitive.bat": intocable
        es_index_panel = (ruta.name.lower() == "index.html" and ruta.parent == HERR)
        ext_ok = ruta.suffix.lower() in BORrables_ext or es_index_panel
        if not ext_ok:
            continue
        # protecciones: nunca borrar este script ni las piezas por diseño
        if ruta.resolve() == Path(__file__).resolve():
            continue
        if stem in {"prepararfotos", "actualizargaleria", "actualizaciondefinitiva", "moverfotosagaleria", "pedido", "pedidops"}:
            # (piezas por diseno; las viejas copias de estas dos primeras viven
            #  en herramientas/ y se eliminan igual con la carpeta, ver abajo)
            continue
        # Proteccion a pedido: NUNCA borrar nada relacionado con las categorias
        # legado / prueba trimestre (jubilar_legado, migrar_legado, etc.).
        if "legado" in stem or ("prueba" in stem and "trimestre" in stem) or "t9test" in stem:
            continue
        if stem == "marcaagua" and ruta.suffix.lower() == ".png":
            continue
        # los tres pasos viejos quedaron consolidados en actualizador.py:
        # si llegaron hasta aqui, se eliminan directo (sus nombres normalizados
        # no coinciden con los patrones de A_BORRAR por la "a" de "definitiva")
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
                # solo herramientas/index.html y variantes "index.bat/.cmd/.ps1" heredadas
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
    # Ademas se eliminan los restos de la consolidacion: las piezas temporales
    # (_c1/_c2/_c3f/_c3g/_trozo*/_ok.flag) que quedaron de armar actualizador.py.
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
    # A pedido: eliminar TODA la carpeta herramientas/. Sus scripts quedaron
    # duplicados en "actualizacion definitive 1/2/3.py" (raiz). Unica excepcion:
    # marca_agua.png, recurso necesario para convertir fotos -> se copia a la
    # raiz antes de borrar la carpeta (asi el paso 2 la encuentra siempre).
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
    # CRLF real para que Windows lo ejecute bien al doble clic.
    bat.write_bytes(BAT_DEFINITIVA.replace("\n", "\r\n").encode("utf-8"))
    hechos.append('Creado "actualizacion definitive.bat" en la raiz (el boton unico: corre actualizador.py)')
    # el boton viejo dentro de herramientas/ ya no sirve (la carpeta se elimina abajo)
    bat_viejo = HERR / "actualizacion_definitiva.bat"
    if bat_viejo.exists():
        try:
            bat_viejo.unlink()
            hechos.append("Eliminado herramientas/actualizacion_definitiva.bat (lo reemplaza el de la raiz)")
        except OSError as e:
            hechos.append(f"No pude borrar herramientas/actualizacion_definitiva.bat: {e}")


# ==================== PASO 2 CONSOLIDADO: conversion de fotos ====================
# ------------------------- AJUSTES (puedes cambiarlos) -------------------------
CALIDAD = 80            # 70 = mas liviano, 85 = mas calidad. Recomendado: 80
LADO_MAXIMO = 1920      # lado mas largo en pixeles. 0 = no reducir
ANCHO_MARCA = 0.6      # ancho de la marca de agua = 60% del ancho de la foto (0.35 = mas pequena)
OPACIDAD = 0.5          # 1 = tal como es tu PNG; mas de 1 = mas visible; menos de 1 = mas tenue
POSICION = "centro"     # "centro" o "abajo-derecha"
# -------------------------------------------------------------------------------

POR_PROCESAR = RAIZ / "por-procesar"
SALIDA_P2 = RAIZ / "fotos"
# El logo se copio a la raiz al eliminar la carpeta herramientas/; durante la
# transicion puede seguir estando ahi tambien.
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


GALERIA = SALIDA_P2 / "galeria"   # unica carpeta que muestra la galeria del sitio


def _nombre_webp(stem):
    """Nombre CANONICO del .webp en la galeria: mismo numero/nombre que la foto
    de por-procesar, pero siempre en minusculas y con espacios -> guiones
    (asi 'IMG_6001.JPG' y 'img_6001.jpg' apuntan al mismo 'img_6001.webp')."""
    return stem.strip().replace(" ", "-").lower()


def _nombre_unico(stem):
    """fotos/galeria/<stem>.webp; si ya existe otro archivo distinto, agrega
    _1, _2... detras (solo pasa si dos fotos diferentes comparten el nombre)."""
    ideal = GALERIA / f"{_nombre_webp(stem)}.webp"
    if not ideal.exists():
        return ideal
    # si "existe" es en realidad el MISMO archivo (mayusculas distintas en
    # Windows), lo reutilizamos: no duplicamos ni agregamos sufijos.
    for p in GALERIA.iterdir():
        if p.stem.lower() == _nombre_webp(stem):
            return p
    base = _nombre_webp(stem)
    i = 1
    destino = GALERIA / f"{base}_{i}.webp"
    while destino.exists():
        i += 1
        destino = GALERIA / f"{base}_{i}.webp"
    return destino


def _existe_en_galeria(canon):
    """True si en fotos/galeria/ ya hay una foto de esta misma foto de
    por-procesar, sin importar mayusculas ni extension (IMG_6001.webp,
    img_6001.JPG o 'foto-9002.webp' cuentan como existente)."""
    for p in GALERIA.iterdir():
        if p.is_file() and p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png") \
                and _nombre_webp(p.stem) == canon:
            return True
    return False


def convertir_todas():
    POR_PROCESAR.mkdir(exist_ok=True)
    GALERIA.mkdir(parents=True, exist_ok=True)
    # Colectar TODAS las fotos de por-procesar/ (recursivo), sin exigir subcarpetas.
    grupos = {}   # clave de subcarpeta -> [archivos]
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
        caja = marca.getchannel("A").getbbox()      # quita los bordes transparentes para centrar bien
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
        for f in archivos:
            origen = f
            canon = _nombre_webp(f.stem)
            if _existe_en_galeria(canon):
                continue                          # esa foto ya esta en la galeria: no se repite
            try:
                if f.suffix.lower() in EXT_RAW:   # RAW -> JPG temporal (primero JPG, luego WebP)
                    if rawpy is None:
                        print(f"  AVISO: {f.name} es RAW y te falta la libreria. Instala: py -m pip install rawpy")
                        continue
                    tmp = RAIZ / "__tmp__" / f"{clave}_{f.stem}.jpg"
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


# ---------------------------------------------------------- espejo exacto (D) --
EXT_FOTO_P2 = EXTENSIONES | EXT_RAW   # todo lo que por-procesar puede contener


def _claves_procesables():
    """Conjuntos de referencia de por-procesar/: stems normales, stems con
    espacio->guion, y stems ya en .webp (para no duplicar ni borrar de mas)."""
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
    base, _, sufijo = n.rpartition("_")        # IMG_6001_1 cuenta como IMG_6001
    return bool(sufijo.isdigit()) and base in claves_normal


def _igualar_mayusculas(stem):
    """Nombre del .webp con el MISMO numero/nombre que la foto de por-procesar,
    conservando sus mayusculas originales (el espejo debe ser exacto: si alla
    dice IMG_6001, aqui debe decir IMG_6001.webp)."""
    canon = _nombre_webp(stem)          # minusculas, espacios -> guiones
    if POR_PROCESAR.is_dir():
        for p in POR_PROCESAR.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXT_FOTO_P2 and _nombre_webp(p.stem) == canon:
                return p.stem.replace(" ", "-")   # nombre original, sin cambiar mayusculas
    return canon


def igualar_galeria_a_por_procesar():
    """Deja fotos/galeria/ con EXACTAMENTE los numeros, nombres y cantidad de
    archivos .webp que corresponden a las fotos de por-procesar/ (a pedido).
    Si por-procesar esta vacio NO toca nada (proteccion: nunca borra tu galeria
    por una carpeta local ausente). Devuelve (renombradas, borradas, faltantes)."""
    renombradas, borradas, faltantes = [], [], []
    claves_normal, claves_guion, webps_locales = _claves_procesables()
    if not claves_normal or not GALERIA.is_dir():
        return renombradas, borradas, faltantes

    # 1) deseados/faltantes: UN .webp por foto de por-procesar, con su nombre exacto
    presentes = {p.name for p in GALERIA.iterdir() if p.is_file()}
    presentes_norm = {p.lower() for p in presentes}   # Windows ignora mayusculas
    deseados = set()
    for canon in sorted(claves_guion):
        destino = f"{_igualar_mayusculas(canon)}.webp"
        deseados.add(destino)
        if destino not in presentes and destino.lower() not in presentes_norm:
            faltantes.append(destino)                  # no existe ni con otras mayusculas

    # 2) sobrantes: cualquier archivo de la galeria que no pertenezca a una
    #    foto de por-procesar, o que sea un duplicado del nombre deseado
    a_borrar, a_renombrar = [], []
    for p in sorted(GALERIA.iterdir()):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in (".webp", ".jpg", ".jpeg", ".png"):
            continue                            # txt u otros: intocables
        if not _pertenece_a_procesar(p.stem, claves_normal, claves_guion):
            a_borrar.append(p)
            continue
        if ext == ".webp":
            ideal = f"{_igualar_mayusculas(p.stem)}.webp"
            if p.name != ideal:                 # el nombre debe quedar EXACTO (igual que por-procesar)
                if _nombre_webp(ideal[:-5]) != _nombre_webp(p.stem):
                    a_borrar.append(p)          # no pertenece al espejo: sobrante
                elif (GALERIA / ideal).exists():
                    a_borrar.append(p)          # duplicado: sobra tras el correcto
                else:
                    a_renombrar.append((p, GALERIA / ideal))
            elif p.name.lower() in deseados and p.name not in deseados:
                a_renombrar.append((p, GALERIA / next(d for d in deseados if d.lower() == p.name.lower())))
        else:
            a_borrar.append(p)                  # jpg/png sobrante: la galeria es webp

    # 3) aplicar primero los renombrados (libera el nombre ideal si esta libre)
    for origen, destino in a_renombrar:
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

    # 4) eliminar los sobrantes
    for p in a_borrar:
        try:
            p.unlink()
            borradas.append(p.name)
        except OSError as e:
            print(f"AVISO (espejo): no pude borrar {p.name}: {e}")

    # 5) verificacion final: la galeria debe ser exactamente el conjunto deseado
    presentes = {p.name for p in GALERIA.iterdir() if p.is_file() and p.suffix.lower() == ".webp"}
    sobran = sorted(p for p in presentes
                    if p not in deseados and p.lower() not in {d.lower() for d in deseados})
    if sobran:
        for nombre in sobran:
            try:
                (GALERIA / nombre).unlink()
                borradas.append(nombre)
            except OSError as e:
                print(f"AVISO (espejo): no pude borrar {nombre}: {e}")
    return renombradas, borradas, faltantes


# ==================== PASO 3 CONSOLIDADO: generador de fotos.js ====================
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


# NOTA: antes este script borraba ciertas etiquetas (moto/casco/caras) al generar fotos.js.
# Se quitó ese filtro a pedido del dueño: el archivo debe respetar tal cual lo que diga
# fotos/etiquetas.txt, porque en el futuro habra funciones que usaran etiquetas parecidas.


def generar_fotos_js():
    """Paso 3: regenera assets/js/fotos.js leyendo fotos/trimestres.txt."""
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
        fotos = sorted(p.name for p in ruta.iterdir() if p.suffix.lower() in EXT_FOTOS)
        seccion = {"id": carpeta, "titulo": titulo, "carpeta": carpeta, "fotos": fotos}
        fechas = fechas_de_seccion(carpeta, fotos, ruta, reglas)
        if fechas:
            seccion["fechas"] = fechas
        ets = etiquetas_de_seccion(fotos, ruta, etiquetas_reglas)
        ets = {f: v for f, v in ets.items() if v}   # descartar fotos que se quedaron sin etiquetas
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


# --------------------------------------------------------------------- main --
def paso_principal():
    """Pasos A-C-F del viejo 'actualizacion definitiva 1.py' + D (espejo) + E (fotos.js)."""
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

    # A) ordenar fotos sueltas hacia fotos/galeria
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

    # B) parches del sitio (webp + galería plus + consolidación)
    print("\n--- B) Parches y consolidación del sitio ---")
    hechos = []
    parche_webp(hechos)
    parche_galeria(hechos)
    consolidar(hechos)
    for h in hechos:
        print("+ " + h)
    if not hechos:
        print("Sitio: los parches ya estaban aplicados (no hice nada).")

    # C) boton unico
    print("\n--- C) Botón único ---")
    hechos_bat = []
    crear_bat(hechos_bat)
    for h in hechos_bat:
        print("+ " + h)

    if paso_final < 2:
        print("\n(Solo se pidio el paso 1: no conversion. Ejecuta el boton sin numero para el flujo completo.)")
        return 0

    # D1) convertir por-procesar -> WebP con marca de agua (viejo paso 2)
    print("\n--- D) Convirtiendo por-procesar/ a WebP (con marca de agua) ---")
    if Image is None:
        print("AVISO: sin Pillow no puedo convertir fotos. Instala: py -m pip install Pillow")
        rc_conv = 2
    else:
        rc_conv = convertir_todas()
    if rc_conv == 1:
        print("(No habia fotos nuevas en por-procesar: la galeria sigue igual.)")

    # D2) espejo EXACTO: fotos/galeria queda con los mismos numeros/nombres/
    #     cantidad de .webp que hay en por-procesar (a pedido)
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

    # E) regenerar la galeria (assets/js/fotos.js)
    print("\n--- E) Regenerando assets/js/fotos.js ---")
    rc = 0
    try:
        generar_fotos_js()
    except BaseException as e:
        print("AVISO: fallo la generacion de fotos.js:", e)
        rc = 1

    # F) eliminar los archivos viejos consolidados (incluidos los pasos 1/2/3)
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
