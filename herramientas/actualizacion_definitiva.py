"""actualizacion_definitiva.py — LA ÚNICA HERRAMIENTA del sitio (borrador).

Consolida en un solo archivo todo lo que antes estaba repartido en:
    preparar_y_actualizar.bat, preparar_fotos.py, pedido.ps1 (parche webp),
    parche_webp.py, parche_galeria.py, migrar_legado.py, marca_agua.png,
    jubilar_legado.py, index.html y consolidar_sitio.py.

Qué hace al ejecutarla (en este orden):
  A) JUBILA "Legado" y "Prueba Trimestre" de la galeria:
       - mueve TODAS las fotos que esten todavia en las carpetas jubiladas
         (fotos/Legado* y fotos/*prueba*/*trimestre*) hacia la carpeta general
         de la galeria: fotos/galeria/ (conserva los nombres; si uno ya existe,
         agrega _1, _2... detras). Las carpetas jubiladas quedan vacias.
       - comenta las lineas de esas secciones en fotos/trimestres.txt,
         fotos/fechas.txt y fotos/etiquetas.txt (los datos quedan guardados;
         se pueden devolver con el argumento --revertir).
       - si quedan las fotos de prueba IMG_9001 / IMG_9002 sin usar, quita
         sus lineas de fotos/etiquetas.txt (las demas etiquetas se conservan).
       - regenera assets/js/fotos.js: las dos secciones dejan de existir en el sitio.
     El movimiento es idempotente: si ya no hay nada en esas carpetas, no hace nada.
  B) Aplica los parches idempotentes del sitio (parche_webp + parche_galeria +
     consolidar_sitio): .webp en el carrito, mosaico mejorado conectado,
     menu/pie/enlaces de Herramientas y estilos.
  C) Regenera herramientas/index.html (el panel de botones actualizado: ahora
     ofrece "Actualizacion definitiva.bat" como boton unico).
  D) Crea herramientas/"actualizacion_definitiva.bat": el nuevo boton unico
     (doble clic) que corre este script y luego convierte fotos nuevas
     (preparar_fotos) y actualiza la galeria (actualizar_galeria), o sea el
     flujo completo de "actualizar todo.bat" mas la jubilacion de Legado.

Uso (consola dentro de la carpeta del proyecto):
    py herramientas/actualizacion_definitiva.py             -> aplica todo
    py herramientas/actualizacion_definitiva.py --revertir  -> devuelve Legado y
        Prueba Trimestre a la galeria (descomenta las lineas jubiladas)

Las piezas que siguen viviendo aparte (por diseño):
  - preparar_fotos.py  : convertido de fotos (necesita herramientas/marca_agua.png,
                        tus originales y Pillow; no tiene sentido fusionarlo aqui).
  - actualizar_galeria.py : generador de fotos.js (este script lo llama).
  - pedido.ps1 : modelo manual del pedido; el boton «Descargar pedido (.ps1)»
                 del carrito sigue generando su propio script.

IMPORTANTE (migracion desde los archivos viejos): si todavia tenes en tu PC
"preparar_y_actualizar.bat" o "actualizar todo.bat", borralos: esta herramienta
crea "actualizacion_definitiva.bat", que es ahora el unico boton del flujo.
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

# Secciones que dejan de existir en la galeria (se comparan en minusculas)
JUBILAR = ["legado", "t9test"]          # t9test = "Prueba Trimestre"
# Fotos de prueba cuya etiqueta conviene quitar al jubilar la seccion
FOTOS_PRUEBA = ["img_9001", "img_9002"]
# Carpetas jubiladas donde pueden estar esas fotos de prueba
CARPETAS_JUBILADAS = JUBILAR
# Carpeta general de la galeria: aca llegan las fotos sacadas de Legado/Prueba
DESTINO_GALERIA = FOTOS / "galeria"
EXT_FOTOS = (".jpg", ".jpeg", ".png", ".webp")

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


def _destino_libre(nombre):
    """fotos/galeria/<nombre>; si ya existe uno, agrega _1, _2... detras."""
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


def mover_fotos_jubiladas():
    """Mueve las fotos de galeria>legado y galeria>prueba trimestre hacia
    la carpeta general fotos/galeria/. Idempotente: si no queda nada, no hace nada."""
    import shutil
    movidas, avisos = [], []
    if FOTOS.is_dir():
        for sub in sorted(FOTOS.iterdir()):
            if not sub.is_dir() or not _es_carjeta_jubilada(sub.name):
                continue
            archivos = sorted(p for p in sub.iterdir()
                              if p.is_file() and p.suffix.lower() in EXT_FOTOS)
            if not archivos:
                continue
            DESTINO_GALERIA.mkdir(exist_ok=True)
            for foto in archivos:
                destino = _destino_libre(foto.name)
                try:
                    shutil.move(str(foto), str(destino))
                    movidas.append(f"{sub.name}/{foto.name} -> galeria/{destino.name}")
                except OSError as e:
                    avisos.append(f"No pude mover {sub.name}/{foto.name}: {e}")
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
    return bool(partes) and partes[0].lower() in claves


def jubilar():
    """Comenta las lineas de las secciones jubiladas (no mueve ni borra fotos)."""
    cambiados = []
    claves = set(JUBILAR)

    if TRIM.exists():
        lineas = TRIM.read_text(encoding="utf-8").splitlines()
        nueva = []
        for ln in lineas:
            if _es_de_seccion(ln.strip(), claves) and not ln.strip().startswith("#"):
                nueva.append("# JUBILADO (antes en la galería): " + ln)
            else:
                nueva.append(ln)
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
    claves = set(JUBILAR)
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
          <p>Lo normal es usar <strong>una sola vez</strong> este botón: mete tus fotos terminadas en
            <code>por-procesar/&lt;trimestre&gt;/</code>, pulsa abajo y al terminar sube los cambios con GitHub Desktop.
            La «Actualización definitiva» además <strong>movió las fotos de Legado y Prueba Trimestre a
            <code>fotos/galeria/</code></strong> y dejó sin efecto esas dos secciones antiguas.</p>
          <div class="jfz-herr-botones">
            <a class="btn-get-started" href="actualizacion_definitiva.bat" download><i class="bi bi-play-circle"></i> Actualización definitiva (todo en uno)</a>
          </div>
          <p class="jfz-note">Si el navegador pregunta, elige «Abrir» o «Conservar». También puedes dar doble clic al archivo en tu explorador de carpetas.</p>

          <h2 class="jfz-sub">Las piezas, por separado</h2>
          <div class="row gy-4 mt-1">
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-gear-wide-connected"></i>
                <h3>Actualización definitiva</h3>
                <p>Script único que mueve las fotos de Legado y Prueba Trimestre a <code>fotos/galeria/</code>, jubila esas secciones, aplica los parches del sitio, consolida los botones y regenera la galería (<code>actualizacion_definitiva.py</code>). Con <code>--revertir</code> devuelve esas secciones.</p>
                <a class="jfz-svc-add" href="actualizacion_definitiva.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-camera-reels"></i>
                <h3>Convertir a WebP</h3>
                <p>RAW / CR2 / JPG &rarr; WebP con marca de agua y fecha EXIF (<code>preparar_fotos.py</code> + <code>marca_agua.png</code>). La «Actualización definitiva» ya lo ejecuta sola.</p>
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
    pag = HERR / "index.html"
    pag.write_text(PAGINA_HERRAMIENTAS, encoding="utf-8")
    hechos.append("herramientas/index.html regenerada (panel actualizado)")

    jfz = RAIZ / "assets" / "js" / "jfz.js"

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
rem    1) actualizacion_definitiva.py  (mueve las fotos de Legado y Prueba
rem       Trimestre a fotos\\galeria, jubila esas secciones, aplica los parches
rem       del sitio y consolida los botones) + regenera la galeria
rem    2) preparar_fotos.py            (fotos nuevas -> WebP con marca
rem       de agua; usa herramientas\\marca_agua.png)
rem    3) actualizar_galeria.py        (regenera assets/js/fotos.js)
rem  Tambien sirve para ejecutar solo UNA pieza intermedia:
rem    "actualizacion_definitiva.bat" 1  -> solo jubilacion + parches
rem    "actualizacion_definitiva.bat" 2  -> hasta convertir fotos
rem    "actualizacion_definitiva.bat" 3  -> todo el flujo (por defecto)
rem  Para DEVOLVER Legado/Prueba Trimestre a la galeria:
rem    py herramientas\\actualizacion_definitiva.py --revertir
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

echo === 1^) Actualizacion definitiva: jubilar Legado/Prueba + parches + galeria ===
%PY% herramientas\\actualizacion_definitiva.py
if errorlevel 1 (echo Hubo un problema en la actualizacion. Avsale a Claude. & goto fin)
if %PASO_FINAL% LSS 2 goto fin
echo.

echo === 2^) Convirtiendo fotos nuevas a WebP ===
%PY% herramientas\\preparar_fotos.py
if errorlevel 2 (echo Hubo un problema al convertir. Avsale a Claude. & goto fin)
if errorlevel 1 echo   ^(no habia fotos nuevas: continuo con la galeria^)
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
        if stem in {"prepararfotos", "actualizargaleria", "actualizaciondefinitiva", "pedido", "pedidops"}:
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
    bat.write_text(BAT_DEFINITIVA, encoding="utf-8")
    hechos.append("Creado herramientas/actualizacion_definitiva.bat (el nuevo botón único)")


def main():
    if "--revertir" in sys.argv:
        rc = revertir()
        return rc or regenerar_galeria()

    print("=== Actualización definitiva (borrador) ===")
    if not (HERR / "marca_agua.png").exists():
        print(MARCA_AGUIO.replace("\n", " "))

    # A) jubilar Legado y Prueba Trimestre (mover sus fotos a galeria + comentar textos)
    print("\n--- A) Jubilando secciones de la galería (fotos -> fotos/galeria) ---")
    mover_fotos_jubiladas()
    jubilar()

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

    # E) regenerar la galeria con las secciones ya jubiladas
    print("\n--- D) Regenerando assets/js/fotos.js ---")
    rc = regenerar_galeria()

    print()
    print('Listo: "Legado" y "Prueba Trimestre" dejaron de existir en la galería.')
    print("Las fotos que quedaban en esas carpetas fueron movidas a fotos/galeria/.")
    print("Si quieres, borra con el explorador de Windows las carpetas jubiladas ya vacías")
    print("(fotos/Legado y fotos/t9test): no afectan al sitio.")
    print('Para el día a día usa herramientas/"actualizacion_definitiva.bat" (doble clic).')
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
