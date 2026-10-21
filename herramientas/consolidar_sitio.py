"""Consolida en un solo lugar los botones de herramientas/ y del sitio. Se puede ejecutar muchas veces sin problema.

Qué hace (cada ajuste es idempotente: si ya está aplicado, no toca nada):
  1. Crea  herramientas/index.html : la página que CONSOLIDA en un solo panel los botones
     del flujo local (ejecutar todo, convertir fotos, actualizar galería, buscador,
     migrar Legado, pedido PowerShell y formatos de las listas).
  2. Menú superior (jfz.js): agrega "Herramientas" antes de "Contacto" y mete la lupa
     de búsqueda dentro del bloque de acciones, junto al carrito y el botón de sesión.
     Orden final de los botones: Inicio | Sobre mí | Galería | Servicios | Herramientas |
     Contacto | [lupa] [carrito] [sesión].
  3. index.html: el botón "Ver galería completa" aterriza directo en el buscador (#buscar).
  4. gallery.html: enlace a la página de herramientas bajo las pestañas; jfz.js enfoca el
     buscador cuando alguien llega con #buscar.
  5. jfz.css: estilos de la lupa del header y de los paneles de herramientas.
  6. Pie de página (jfz.js): enlace "Herramientas del fotógrafo".
  7. preparar_y_actualizar.bat: ejecuta este script primero, para que el sitio quede
     siempre consolidado después de cada actualización.

Uso manual (normalmente basta con preparar_y_actualizar.bat):
    py herramientas/consolidar_sitio.py
Si algún día editas esas partes a mano y aparece un aviso "no encontré ...", avísale a Claude.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

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
      </div>
      <nav class="breadcrumbs">
        <div class="container">
          <ol>
            <li><a href="../index.html">Inicio</a></li>
            <li class="current">Herramientas</li>
          </ol>
        </div>
      </nav>
    </div>

    <section id="herramientas" class="gallery section">
      <div class="container" data-aos="fade-up">
        <div class="jfz-panel">
          <h2><i class="bi bi-tool"></i> Un solo botón para todo</h2>
          <p>Lo normal es usar <strong>una sola vez</strong> este botón: mete tus fotos terminadas en
            <code>por-procesar/&lt;trimestre&gt;/</code>, pulsa abajo y al terminar sube los cambios con GitHub Desktop.</p>
          <div class="jfz-herr-botones">
            <a class="btn-get-started" href="preparar_y_actualizar.bat" download><i class="bi bi-play-circle"></i> Ejecutar todo (convertir + actualizar)</a>
          </div>
          <p class="jfz-note">Si el navegador pregunta, elige «Abrir» o «Conservar». También puedes dar doble clic al archivo en tu explorador de carpetas.</p>

          <h2 class="jfz-sub">Las piezas, por separado</h2>
          <div class="row gy-4 mt-1">
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-camera-reels"></i>
                <h3>Convertir a WebP</h3>
                <p>RAW / CR2 / JPG &rarr; WebP con marca de agua y fecha EXIF (<code>preparar_fotos.py</code>).</p>
                <a class="jfz-svc-add" href="preparar_fotos.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-collection"></i>
                <h3>Actualizar galería</h3>
                <p>Regenera <code>assets/js/fotos.js</code> con fechas, etiquetas y trimestres (<code>actualizar_galeria.py</code>).</p>
                <a class="jfz-svc-add" href="actualizar_galeria.py" download><i class="bi bi-download"></i> Descargar script</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-search"></i>
                <h3>Buscar fotos (oculto)</h3>
                <p>El buscador con filtros y las etiquetas #moto / #casco / #caras quedaron ocultos a pedido del dueño.</p>
                <a class="jfz-svc-add" href="../gallery.html"><i class="bi bi-arrow-right-circle"></i> Ir a la galería</a>
              </div>
            </div>
            <div class="col-md-6 col-xl-4">
              <div class="jfz-serv">
                <i class="bi bi-box-arrow-right"></i>
                <h3>Migrar Legado</h3>
                <p>Pasa las fotos de <code>fotos/Legado</code> a <code>por-procesar/legado</code> para jubilar la carpeta (<code>migrar_legado.py</code>).</p>
                <a class="jfz-svc-add" href="migrar_legado.py" download><i class="bi bi-download"></i> Descargar script</a>
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
            <p class="jfz-note">Después de editar cualquiera de estos archivos, vuelve a pulsar «Ejecutar todo».</p>
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

LUPA = '<a class="jfz-buscabox" href="gallery.html#buscar" aria-label="Buscar fotos" title="Buscar fotos"><i class="bi bi-search"></i></a>'


def _reemplazo(ruta, viejo, nuevo, etiqueta, hechos):
    """Reemplaza `viejo` por `nuevo` una sola vez. Idempotente de verdad: si `nuevo`
    ya está en el archivo (aunque `viejo` siga apareciendo dentro de él), no toca nada."""
    s = ruta.read_text(encoding="utf-8")
    if nuevo in s:
        return
    if viejo not in s:
        print(f"AVISO ({etiqueta}): no encontré el texto esperado en {ruta.name} (¿lo editaste a mano?). Avísale a Claude.")
        return
    ruta.write_text(s.replace(viejo, nuevo, 1), encoding="utf-8")
    hechos.append(etiqueta)


def main():
    hechos = []

    # --- 1. Página nueva: herramientas/index.html (botones consolidados) ---
    pag = RAIZ / "herramientas" / "index.html"
    if not pag.exists():
        pag.write_text(PAGINA_HERRAMIENTAS, encoding="utf-8")
        hechos.append("herramientas/index.html creada (panel único de botones)")
    else:
        print("herramientas/index.html: ya existe (si quieres regenerarla, bórrala y repite).")

    # --- 2. Header: "Herramientas" en el menú (la lupa de búsqueda se QUITÓ a pedido del dueño) ---
    jfz = RAIZ / "assets" / "js" / "jfz.js"
    nav_viejo = '\'<li><a href="contact.html"\' + act("contacto") + ">Contacto</a></li>"'
    nav_nuevo = '\'<li><a href="herramientas/index.html"\' + act("herramientas") + ">Herramientas</a></li>" +\n      ' + nav_viejo
    _reemplazo(jfz, nav_viejo, nav_nuevo, "Menú: enlace «Herramientas» agregado", hechos)

    # la lupa ya NO va en el header: si estaba puesta, se quita (barra de búsqueda eliminada a pedido)
    s = jfz.read_text(encoding="utf-8")
    if LUPA in s:
        jfz.write_text(s.replace(LUPA, "", 1), encoding="utf-8")
        hechos.append("Header: lupa de búsqueda quitada (el buscador quedó oculto a pedido)")

    # --- 3. index.html: el botón principal ya NO apunta al buscador (buscador oculto a pedido) ---
    _reemplazo(RAIZ / "index.html",
               '<a href="gallery.html#buscar" class="btn-get-started">Ver galería completa</a>',
               '<a href="gallery.html" class="btn-get-started">Ver galería completa</a>',
               "index.html: «Ver galería completa» vuelve a apuntar a la galeria normal", hechos)

    # --- 4. gallery.html: enlace a la página de herramientas bajo las pestañas ---
    _reemplazo(RAIZ / "gallery.html",
               '<div class="jfz-tabs" id="jfz-tabs"></div>',
               '<div class="jfz-tabs" id="jfz-tabs"></div>\n        <div class="jfz-tabs-linea"><a href="herramientas/index.html" class="jfz-herr-enlace"><i class="bi bi-tool"></i> Herramientas</a></div>',
               "gallery.html: enlace a Herramientas agregado", hechos)

    # --- 5. jfz.js: llegar con #buscar enfoca el buscador ---
    s = jfz.read_text(encoding="utf-8")
    if 'hash === "#buscar"' not in s:
        viejo_fin = 'window.addEventListener("hashchange", showTab);'
        nuevo_fin = (viejo_fin + "\n    if (location.hash === \"#buscar\") { setTimeout(function () { var bq = $(\"#jfz-q\"); if (bq) { try { bq.scrollIntoView({ behavior: \"smooth\", block: \"center\" }); } catch (e) {} bq.focus({ preventScroll: true }); } }, 80); }")
        if viejo_fin in s:
            jfz.write_text(s.replace(viejo_fin, nuevo_fin, 1), encoding="utf-8")
            hechos.append("jfz.js: el enlace #buscar hace scroll y enfoca el buscador")
        else:
            print('AVISO (#buscar): no encontré "hashchange" en jfz.js. Avísale a Claude.')

    # --- 6. Pie de página: enlace a Herramientas ---
    s = jfz.read_text(encoding="utf-8")
    pie_viejo = '\'<div class="credits">'
    pie_nuevo = ('\'<div class="jfz-pie-herr"><a href="herramientas/index.html"><i class="bi bi-tool"></i> Herramientas del fotógrafo</a></div>\' +\n        ' + pie_viejo)
    if "jfz-pie-herr" not in s:
        if pie_viejo in s:
            jfz.write_text(s.replace(pie_viejo, pie_nuevo, 1), encoding="utf-8")
            hechos.append("Pie de página: enlace a Herramientas agregado")
        else:
            print("AVISO (pie): no encontré la sección «credits» del footer en jfz.js. Avísale a Claude.")

    # --- 7. jfz.css: estilos de la lupa y de los paneles de herramientas ---
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
        hechos.append("jfz.css: estilos de la lupa y del panel de herramientas")

    # --- 8. preparar_y_actualizar.bat: correr la consolidación primero ---
    bat = RAIZ / "herramientas" / "preparar_y_actualizar.bat"
    sbat = bat.read_text(encoding="utf-8")
    if "consolidar_sitio.py" not in sbat:
        sbat = sbat.replace("echo === 1/3 Parche del sitio ===",
                            "echo === 0/3 Consolidando botones del sitio ===\npy herramientas\\consolidar_sitio.py\necho.\necho === 1/3 Parche del sitio ===")
        bat.write_text(sbat, encoding="utf-8")
        hechos.append("preparar_y_actualizar.bat: ahora consolida los botones en cada ejecución")

    if hechos:
        for h in hechos:
            print("+ " + h)
        print("Consolidación aplicada. Si viste AVISOS arriba, avísale a Claude (no rompí nada más).")
    else:
        print("Sitio: los botones ya estaban consolidados (no hice nada).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
