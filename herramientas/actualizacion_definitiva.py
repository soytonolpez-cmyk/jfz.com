"""actualizacion_definitiva.py — LA ÚNICA HERRAMIENTA del sitio.

Consolida en un solo archivo todo lo que antes estaba repartido en:
    preparar_y_actualizar.bat, preparar_fotos.py, pedido.ps1 (parche webp),
    parche_webp.py, parche_galeria.py, migrar_legado.py, marca_agua.png,
    jubilar_legado.py, index.html, consolidar_sitio.py y mover_fotos_a_galeria.py.

Qué hace al ejecutarla (en este orden):
  A) ORDENA la carpeta fotos/: cualquier foto suelta (o dentro de subcarpetas
     como t4/) se mueve a la carpeta general fotos/galeria/ — la unica seccion
     que existe ahora en el sitio. Idempotente: si ya esta todo ordenado, no toca nada.
  A2) QUITADO a pedido: antes jubilaba "Legado" y "Prueba Trimestre" (movia sus
       fotos a fotos/galeria/ y comentaba sus lineas en los .txt). Ahora el boton
       NO toca nada de eso; esas categorias quedan intactas. El codigo sigue
       disponible solo para reactivarlo a mano con el argumento --jubilar-legacy
       (--revertir sigue funcionando para devolver secciones ya jubiladas).
  B) Aplica los parches idempotentes del sitio (parche_webp + parche_galeria +
     consolidar_sitio): .webp en el carrito, mosaico mejorado conectado,
     menu/pie/enlaces de Herramientas y estilos.
  C) Regenera herramientas/index.html (el panel de botones actualizado: ahora
     ofrece "Actualizacion definitiva.bat" como boton unico).
  D) Crea herramientas/"actualizacion_definitiva.bat": el nuevo boton unico
     (doble clic) que corre este script y luego convierte fotos nuevas
     (preparar_fotos) y actualiza la galeria (actualizar_galeria). Ya no
     jubila Legado: esa parte del flujo fue quitada a pedido.

Uso (consola dentro de la carpeta del proyecto):
    py herramientas/actualizacion_definitiva.py             -> aplica todo
        (Legado y Prueba Trimestre quedan SIN tocar)
    py herramientas/actualizacion_definitiva.py --jubilar-legacy -> reactiva a
        mano la jubilacion de esas secciones (movia sus fotos a galeria)
    py herramientas/actualizacion_definitiva.py --revertir  -> devuelve Legado y
        Prueba Trimestre a la galeria (descomenta las lineas jubiladas)

PASO A PASO PARA SUBIR FOTOS NUEVAS (lo que usas dia a dia):
    1. Mete tus fotos terminadas (JPG/PNG/HEIC/RAW) en por-procesar\\ (sueltas
       o en carpetas, ej. por-procesar\\t4\\). Esa carpeta NO se sube a GitHub.
    2. Doble clic a herramientas\\actualizacion_definitiva.bat: prepara las
       fotos con marca de agua en fotos\\galeria\\ y regenera la galeria.
    3. GitHub Desktop -> Commit to main -> Push origin. En jfz.com se ven solas.

Las piezas que siguen viviendo aparte (por diseño):
  - preparar_fotos.py  : convertido de fotos (necesita herramientas/marca_agua.png,
                        tus originales y Pillow; guarda directo en fotos/galeria/).
  - actualizar_galeria.py : generador de fotos.js (este script lo llama).
  - pedido.ps1 : modelo manual del pedido; el boton «Descargar pedido (.ps1)»
                 del carrito sigue generando su propio script.

IMPORTANTE (migracion desde los archivos viejos): si todavia tenes en tu PC
"preparar_y_actualizar.bat", "actualizar todo.bat" o "mover_fotos_a_galeria.bat",
borralos: esta herramienta crea "actualizacion_definitiva.bat", que es ahora el
unico boton del flujo (y mover_fotos_a_galeria se elimina solo al ejecutarla).
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
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

MARCA_AGUIO = """AVISO: no encontre herramientas/marca_agua.png. Preparar fotos
avisa si falta; para convertir necesitas ahi tu logo PNG transparente."""


def _normalizar(s):
    import unicodedata
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


# ------------------------------------------------------------- fotos.js (B/C) --
def regenerar_galeria():
    r = subprocess.run([sys.executable, str(HERR / "actualizar_galeria.py")], cwd=RAIZ)
    if r.returncode != 0:
        print("AVISO: actualizar_galeria.py falló; revisa lo anterior e inténtalo otra vez.")
    return r.returncode


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


PAGINA_HERRAMIENTAS = """<!DOCTYPE html>
<html lang="es-419">

<head>
  <meta charset="utf-8">
  <meta content="width=device-width, initial-scale=1.0" name="viewport">
  <title>Herramientas | JuanetoFZ</title>
  <meta name="description" content="Botones consolidados de las herramientas locales del sitio.">

  <!-- Íconos del sitio -->
  <link href="../assets/img/favicon.png" rel="icon">
  <link href="../assets/img/apple-touch-icon.png" rel="apple-touch-icon">

  <!-- Tipografías: Bebas Neue (títulos), Oswald (menú), Roboto (texto) -->
  <link href="https://fonts.googleapis.com" rel="preconnect">
  <link href="https://fonts.gstatic.com" rel="preconnect" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Bebas+Neue&family=Oswald:wght@400;500;600&display=swap" rel="stylesheet">

  <!-- CSS de librerías -->
  <link href="../assets/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet">
  <link href="../assets/vendor/bootstrap-icons/bootstrap-icons.css" rel="stylesheet">
  <link href="../assets/vendor/aos/aos.css" rel="stylesheet">
  <link href="../assets/vendor/glightbox/css/glightbox.min.css" rel="stylesheet">
  <link href="../assets/vendor/swiper/swiper-bundle.min.css" rel="stylesheet">

  <!-- CSS principal y personalización JuanetoFZ -->
  <link href="../assets/css/main.css" rel="stylesheet">
  <link href="../assets/css/jfz.css" rel="stylesheet">
</head>

<body data-page="herramientas">

  <!-- El menú superior se genera en ../assets/js/jfz.js -->
  <header id="header" class="header d-flex align-items-center sticky-top"></header>

  <main class="main">

    <!-- Título de la página -->
    <div class="page-title" data-aos="fade">
      <div class="heading">
        <div class="container">
          <div class="row d-flex justify-content-center text-center">
            <div class="col-lg-8">
              <h1>Herramientas</h1>
              <p class="mb-0">Todos los botones de mi flujo local, consolidados en un solo lugar.</p>
            </div>
          </div>
        </div>
      </nav>
    </div>

    <section id="herramientas" class="gallery section">
      <div class="container" data-aos="fade-up">
        <div class="jfz-panel">
          <h2><i class="bi bi-tool"></i> Un solo botón para todo</h2>
          <p>Así subo mis fotos terminadas a la galería con marca de agua:</p>
          <ol class="jfz-pasos">
            <li>Mete tus fotos (JPG, PNG, HEIC o RAW: CR2, CR3, NEF...) dentro de <code>por-procesar/</code>, sueltas o en carpetas (ej. <code>por-procesar/t4/</code>). Esa carpeta <strong>no se sube a GitHub</strong>: tus originales quedan solo en tu PC.</li>
            <li>Pulsa el botón de abajo (doble clic al archivo también sirve). Convierte las fotos a WebP <strong>con marca de agua</strong>, las deja en <code>fotos/galeria/</code> y regenera la galería.</li>
            <li>Abre GitHub Desktop &rarr; «Commit to main» &rarr; «Push origin». En 1-2 minutos se ven en jfz.com.</li>
          </ol>
          <div class="jfz-herr-botones">
            <a class="btn-get-started" href="actualizacion_definitiva.bat" download><i class="bi bi-play-circle"></i> Actualización definitiva (todo en uno)</a>
          </div>
          <p class="jfz-note">Si el navegador pregunta, elige «Abrir» o «Conservar». Las fotos que ya estaban convertidas no se repiten; los nombres repetidos reciben _1, _2... automáticamente.</p>

          <h2 class="jfz-sub">Las piezas, por separado</h2>
          <div class="row gy-4 mt-1">
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-gear-wide-connected"></i>
                <h3>Actualización definitiva</h3>
                <p>Script único que ordena las fotos sueltas en <code>fotos/galeria/</code>, aplica los parches del sitio, consolida los botones y regenera la galería (<code>actualizacion_definitiva.py</code>). Las categorías Legado y Prueba Trimestre quedan sin tocar (la jubilación solo se reactiva a mano con <code>--jubilar-legacy</code>).</p>
                <a class="jfz-svc-add" href="actualizacion_definitiva.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-camera-reels"></i>
                <h3>Convertir a WebP</h3>
                <p>RAW / CR2 / JPG / HEIC &rarr; WebP con marca de agua y fecha EXIF, directo a <code>fotos/galeria/</code> (<code>preparar_fotos.py</code> + <code>marca_agua.png</code>). La «Actualización definitiva» ya lo ejecuta sola.</p>
                <a class="jfz-svc-add" href="preparar_fotos.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-collection"></i>
                <h3>Actualizar galería</h3>
                <p>Regenera <code>assets/js/fotos.js</code> con fechas, etiquetas y trimestres (<code>actualizar_galeria.py</code>). La «Actualización definitiva» ya lo ejecuta sola.</p>
                <a class="jfz-svc-add" href="actualizar_galeria.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-bag-check"></i>
                <h3>Pedido + originales</h3>
                <p>El botón «Descargar pedido (.ps1)» del carrito genera un script de PowerShell que copia los <strong>originales</strong> (RAW/CR2/JPG) del pedido desde <code>por-procesar/</code> a una carpeta de entrega. Aquí tienes también el modelo manual: pásale los nombres como argumentos.</p>
                <a class="jfz-svc-add" href="../carrito.html"><i class="bi bi-cart3"></i> Ir al carrito</a>
                <a class="jfz-svc-add" href="pedido.ps1" download><i class="bi bi-download"></i> Descargar pedido.ps1</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-tags"></i>
                <h3>Listas de datos</h3>
                <p>Los archivos <code>trimestres.txt</code>, <code>fechas.txt</code> y <code>etiquetas.txt</code> están en la carpeta <code>fotos/</code>. Sus formatos, abajo.</p>
                <a class="jfz-svc-add" href="#listas"><i class="bi bi-journal-text"></i> Ver formatos</a>
              </div>
            </div>
          </div>

          <h2 class="jfz-sub" id="listas">Formatos de las listas (carpeta fotos/)</h2>
          <div class="jfz-panel jfz-herr-notas">
            <p><strong>trimestres.txt</strong> — una línea por sección: <code>t4 | 4to Trimestre 2026</code></p>
            <p><strong>fechas.txt</strong> — <code>t4 | IMG_6001 | 2026-08-15</code> (también acepta rangos: <code>IMG_6001 a IMG_6020</code>)</p>
            <p><strong>etiquetas.txt</strong> — <code>IMG_6001 | moto, casco</code> (las mismas palabras que usan los botones #moto #casco #caras)</p>
            <p class="jfz-note">Después de editar cualquiera de estos archivos, vuelve a pulsar «Actualización definitiva».</p>
          </div>

          <h2 class="jfz-sub" id="orden">El orden en herramientas/ (resumido)</h2>
          <div class="jfz-panel jfz-herr-notas">
            <p><strong>Tú solo usas un archivo:</strong> <code>actualizacion_definitiva.bat</code> (doble clic). Los demás son sus piezas internas o recursos:</p>
            <p><code>actualizacion_definitiva.py</code> — el cerebro (jubila secciones, parchea el sitio, regenera todo)</p>
            <p><code>preparar_fotos.py</code> + <code>marca_agua.png</code> — conversión con marca de agua (el .bat lo llama solo)</p>
            <p><code>actualizar_galeria.py</code> — generador de fotos.js (el .bat lo llama solo)</p>
            <p><code>pedido.ps1</code> — modelo manual para entregar originales (lo normal es usar el botón del carrito)</p>
            <p><code>index.html</code> — esta misma página (se regenera sola)</p>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- El pie de página se genera en ../assets/js/jfz.js -->
  <footer id="footer" class="footer"></footer>

  <a href="#" id="scroll-top" class="scroll-top d-flex align-items-center justify-content-center"><i class="bi bi-arrow-up-short"></i></a>

  <!-- JS de librerías -->
  <script src="../assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
  <script src="../assets/vendor/aos/aos.js"></script>
  <script src="../assets/vendor/glightbox/js/glightbox.min.js"></script>
  <script src="../assets/vendor/swiper/swiper-bundle.min.js"></script>

  <!-- JS de JuanetoFZ (el orden importa: config, fotos, jfz y al final main) -->
  <script src="../assets/js/config.js"></script>
  <script src="../assets/js/servicios.js"></script>
  <script src="../assets/js/fotos.js"></script>
  <script src="../assets/js/jfz.js"></script>
  <script src="../assets/js/main.js"></script>

</body>

</html>
"""


def consolidar(hechos):
    """Equivalente a consolidar_sitio.py (parches del sitio, página de herramientas)."""
    # 1) Panel de herramientas: siempre se regenera (esta versión es la definitiva)
    HERR.mkdir(exist_ok=True)
    pag = HERR / "index.html"
    pag.write_text(PAGINA_HERRAMIENTAS, encoding="utf-8")
    hechos.append("herramientas/index.html regenerada (panel actualizado)")

    jfz = RAIZ / "assets" / "js" / "jfz.js"
    if not jfz.exists():
        print("AVISO: no encontré assets/js/jfz.js en este proyecto; salto los parches del sitio. Avísale a Claude.")
        return

    # 2) Menú: enlace "Herramientas" antes de Contacto (si no estaba ya)
    jfz_txt = jfz.read_text(encoding="utf-8")
    if 'href=\\"herramientas/index.html\\"' in jfz_txt or 'href="herramientas/index.html"' in jfz_txt:
        pass  # el enlace ya está puesto (consolidación anterior): no duplicar
    else:
        nav_viejo = '\'<li><a href="contact.html"\' + act("contacto") + ">Contacto</a></li>"'
        nav_nuevo = '\'<li><a href="herramientas/index.html"\' + act("herramientas") + ">Herramientas</a></li>"' + "\\n      " + nav_viejo
        _reemplazo(jfz, nav_viejo, nav_nuevo, "Menú: enlace «Herramientas» agregado", hechos)

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

    # 4) gallery.html: enlace a la página de herramientas bajo las pestañas
    gal = RAIZ / "gallery.html"
    gtxt = gal.read_text(encoding="utf-8")
    if 'href="herramientas/index.html"' in gtxt:
        pass  # el enlace ya está puesto (consolidación anterior): no duplicar
    else:
        _reemplazo(gal,
                   '<div class="jfz-tabs" id="jfz-tabs"></div>',
                   '<div class="jfz-tabs" id="jfz-tabs"></div>\n        <div class="jfz-tabs-linea"><a href="herramientas/index.html" class="jfz-herr-enlace"><i class="bi bi-tool"></i> Herramientas</a></div>',
                   "gallery.html: enlace a Herramientas agregado", hechos)

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

    # 6) Pie de página: enlace a Herramientas
    s = jfz.read_text(encoding="utf-8")
    pie_viejo = '\'<div class="credits">'
    pie_nuevo = ('\'<div class="jfz-pie-herr"><a href="herramientas/index.html"><i class="bi bi-tool"></i> Herramientas del fotógrafo</a></div>\' +' + "\\n        " + pie_viejo)
    if "jfz-pie-herr" not in s:
        if pie_viejo in s:
            jfz.write_text(s.replace(pie_viejo, pie_nuevo, 1), encoding="utf-8")
            hechos.append("Pie de página: enlace a Herramientas agregado")
        else:
            print("AVISO (pie): no encontré la sección «credits» del footer en jfz.js. Avísale a Claude.")

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
rem  "actualizacion_definitiva.bat" - EL BOTON UNICO de este sitio.
rem  Doble clic y hace TODO el flujo automatico, en orden:
rem    1) actualizacion_definitiva.py  (mueve las fotos sueltas que queden
rem       dentro de fotos\\ en la carpeta general fotos\\galeria, aplica los
rem       parches del sitio y consolida los botones)
rem    2) preparar_fotos.py            (fotos de por-procesar\\ -> WebP con
rem       marca de agua en fotos\\galeria; usa herramientas\\marca_agua.png)
rem    3) actualizar_galeria.py        (regenera assets/js/fotos.js)
rem  Despues: GitHub Desktop -> Commit to main -> Push origin.
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizacion_definitiva.bat" 1  -> solo parches
rem    "actualizacion_definitiva.bat" 2  -> hasta convertir fotos
rem    "actualizacion_definitiva.bat" 3  -> todo el flujo (por defecto)
rem  NOTA: se quito del flujo el codigo que jubilaba/borraba las categorias
rem  legado y prueba trimestre (ya no se toca nada de eso).
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

rem --- elige el interprete de Python (py = el lanzador de Windows; si no, python) ---
set PY=py
where py >nul 2>nul || set PY=python

rem --- paso final por defecto: 3 = todo el flujo; acepta un numero como argumento ---
set PASO_FINAL=3
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-3]$" >nul && set PASO_FINAL=%~1
)

echo === 1^) Actualizacion definitiva: ordenar fotos + parches ===
%PY% herramientas\\actualizacion_definitiva.py
if errorlevel 1 (echo Hubo un problema en la actualizacion. Avsale a Claude. & goto fin)
if %PASO_FINAL% LSS 2 goto fin
echo.

echo === 2^) Convirtiendo fotos nuevas a WebP (con marca de agua) ===
%PY% herramientas\\preparar_fotos.py
if errorlevel 2 (echo Hubo un problema al convertir. Avsale a Claude. & goto fin)
if errorlevel 1 echo   ^(no habia fotos nuevas en por-procesar: continuo con la galeria^)
if %PASO_FINAL% LSS 3 goto fin
echo.

echo === 3^) Actualizando la galeria ===
%PY% herramientas\\actualizar_galeria.py

:fin
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
    "index",                   # paneles viejos: index.html/.bat fuera de herramientas/ NO;
                               # solo herramientas/index.html y cualquier "index.bat" heredado
    "consolidar_sitio",
    "actualizar todo",         # .bat/.cmd/.ps1
    "mover_fotos_a_galeria",   # incluido en el flujo del boton unico (preparar_fotos ya guarda en galeria)
]

def _norm(s):
    import unicodedata
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
        es_index_panel = (ruta.name.lower() == "index.html" and ruta.parent == HERR)
        ext_ok = ruta.suffix.lower() in BORrables_ext or es_index_panel
        if not ext_ok:
            continue
        # protecciones: nunca borrar este script ni las piezas por diseño
        if ruta.resolve() == Path(__file__).resolve():
            continue
        if stem in {"prepararfotos", "actualizargaleria", "actualizaciondefinitiva", "moverfotosagaleria", "pedido", "pedidops"}:
            continue
        # Proteccion a pedido: NUNCA borrar nada relacionado con las categorias
        # legado / prueba trimestre (jubilar_legado, migrar_legado, etc.).
        if "legado" in stem or ("prueba" in stem and "trimestre" in stem) or "t9test" in stem:
            continue
        if stem == "marcaagua" and ruta.suffix.lower() == ".png":
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
                    hechos.append(f"Eliminado {ruta.relative_to(RAIZ)} (consolidado en actualizacion_definitiva)")
                except OSError as e:
                    hechos.append(f"No pude borrar {ruta.relative_to(RAIZ)}: {e}")
                break


def crear_bat(hechos):
    bat = HERR / "actualizacion_definitiva.bat"
    # CRLF real para que Windows lo ejecute bien al doble clic.
    bat.write_bytes(BAT_DEFINITIVA.replace("\n", "\r\n").encode("utf-8"))
    hechos.append("Creado herramientas/actualizacion_definitiva.bat (el nuevo botón único)")


def main():
    if "--revertir" in sys.argv:
        rc = revertir()
        return rc or regenerar_galeria()

    print("=== Actualización definitiva (borrador) ===")
    if not (HERR / "marca_agua.png").exists():
        print(MARCA_AGUIO.replace("\n", " "))

    # A) ordenar fotos sueltas + jubilar Legado y Prueba Trimestre (mover sus fotos a galeria + comentar textos)
    print("\n--- A) Ordenando la carpeta fotos/ hacia fotos/galeria ---")
    mov, av = ordenar_fotos()
    for m in mov:
        print("+ Foto ordenada a la galería general: " + m)
    for a in av:
        print("AVISO: " + a)
    if not mov and not av:
        print("fotos/ ya estaba ordenada: todas las fotos viven en fotos/galeria/.")
    # QUITADO a pedido: antes aca estaba el codigo que jubilaba/borraba las
    # categorias legado y prueba trimestre (mover_fotos_jubiladas() + jubilar()).
    # Ya no forma parte del boton "actualizacion_definitiva.bat": nada de eso se
    # mueve, comenta ni borra al ejecutarlo. (Solo puede reactivarse a mano con:
    #   py herramientas/actualizacion_definitiva.py --jubilar-legacy)
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

    # D) eliminar de una vez todos los archivos consolidados que todavia existan
    hechos_lim = []
    limpiar_viejos(hechos_lim)
    for h in hechos_lim:
        print("+ " + h)
    if not hechos_lim:
        print("Limpieza: no quedaba ningún archivo viejo por eliminar.")
    # (por las dudas, botones heredados también en la raiz del proyecto)
    for viejo_boton in ("preparar_y_actualizar.bat", "actualizar todo.bat"):
        for ruta_boton in (HERR / viejo_boton, RAIZ / viejo_boton):
            if ruta_boton.exists():
                ruta_boton.unlink()
                print(f"+ Eliminado el boton heredado {ruta_boton.name} (ahora existe actualizacion_definitiva.bat)")

    # E) regenerar la galeria (Legado/Prueba Trimestre quedan intactas por defecto)
    print("\n--- D) Regenerando assets/js/fotos.js ---")
    rc = regenerar_galeria()

    print()
    if "--jubilar-legacy" in sys.argv:
        print('Listo: "Legado" y "Prueba Trimestre" dejaron de existir en la galería.')
        print("Las fotos que quedaban en esas carpetas fueron movidas a fotos/galeria/.")
        print("Si quieres, borra con el explorador de Windows las carpetas jubiladas ya vacías")
        print("(fotos/Legado y fotos/t9test): no afectan al sitio.")
    else:
        print('Listo: las categorías "Legado" y "Prueba Trimestre" quedaron SIN tocar.')
        print("(la jubilación solo se ejecuta a mano con --jubilar-legacy).")
    print('Para el día a día usa herramientas/"actualizacion_definitiva.bat" (doble clic).')
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
