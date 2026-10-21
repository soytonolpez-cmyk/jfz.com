/* JuanetoFZ — encabezado, pie, galería por trimestres, carrito, login con Google y envío por WhatsApp */
(function () {
  "use strict";
  var C = window.JFZ_CONFIG, S = window.JFZ_FOTOS || [];
  var RUTA = "fotos/";
  var MAPA = {};   // nombre de archivo -> ruta completa (carpeta del trimestre)
  S.forEach(function (s) { s.fotos.forEach(function (f) { if (!MAPA[f]) MAPA[f] = RUTA + s.carpeta + "/" + f; }); });
  var user = null, cart = [], pending = null, auth = null, fb = null, lightbox = null;
  var ORIGINALES = "por-procesar";   // carpeta local donde viven los originales (RAW/JPG); se puede cambiar con window.JFZ_ORIGINALES
  if (typeof window.JFZ_ORIGINALES === "string" && window.JFZ_ORIGINALES) ORIGINALES = window.JFZ_ORIGINALES;
  var demo = location.protocol === "file:" || !C.FIREBASE || !C.FIREBASE.apiKey || /PEGA/.test(C.FIREBASE.apiKey);

  /* ---------- utilidades ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function money(n) { return "$" + Number(n).toLocaleString("es-CO"); }
  function base(f) { return f.replace(/\.(jpe?g|png|webp)$/i, ""); }
  var SERV = {};
  (C.SERVICIOS || []).forEach(function (x) { SERV[x.id] = x; });
  function isSvc(x) { return x.indexOf("svc:") === 0; }
  function svc(x) { return SERV[x.slice(4)]; }
  function valid(x) { return isSvc(x) ? !!svc(x) : !!MAPA[x]; }
  function photos() { return cart.filter(function (x) { return !isSvc(x); }); }
  function svcs() { return cart.filter(isSvc).map(svc); }
  function label(x) { return isSvc(x) ? svc(x).nombre : base(x); }
  function ruta(f, c) { return c ? RUTA + c + "/" + f : (MAPA[f] || RUTA + f); }
  function unit(n) { var p = 0; C.PRECIOS.forEach(function (t) { if (n >= t.desde) p = t.precio; }); return p; }
  function toast(msg) {
    var t = $("#jfz-toast"); if (!t) { t = document.createElement("div"); t.id = "jfz-toast"; document.body.appendChild(t); }
    t.textContent = msg; t.className = "show"; clearTimeout(t._h); t._h = setTimeout(function () { t.className = ""; }, 2600);
  }

  /* ---------- encabezado y pie ---------- */
  function renderChrome() {
    var p = document.body.getAttribute("data-page") || "";
    var act = function (k) { return p === k ? ' class="active"' : ""; };
    /* A pedido del dueño: el menú «Galería» ya NO despliega una sub-opción con el
       mismo nombre. Si una sección se llama igual que la página («Galería»), se omite;
       las demás (trimestres, sesiones) siguen apareciendo en el desplegable. */
    var sub = S.filter(function (s) { return String(s.titulo).trim().toLowerCase() !== "galeria" && String(s.id).toLowerCase() !== "galeria"; })
      .map(function (s) { return '<li><a href="gallery.html#' + s.id + '">' + esc(s.titulo) + "</a></li>"; }).join("");
    var h = $("#header");
    if (h) h.innerHTML =
      '<div class="container-fluid position-relative d-flex align-items-center justify-content-between">' +
      '<a href="index.html" class="logo d-flex align-items-center me-auto me-xl-0"><img src="assets/img/logo.png" alt="Logo JFZ"><h1 class="sitename">JuanetoFZ</h1></a>' +
      '<nav id="navmenu" class="navmenu"><ul>' +
      '<li><a href="index.html"' + act("inicio") + ">Inicio</a></li>" +
      '<li><a href="index.html#sobre-mi">Sobre mí</a></li>' +
      '<li class="dropdown"><a href="gallery.html"' + act("galeria") + '><span>Galería</span> <i class="bi bi-chevron-down toggle-dropdown"></i></a><ul>' + sub + "</ul></li>" +
      '<li><a href="services.html"' + act("servicios") + ">Servicios</a></li>" +
      /* Enlace «Herramientas» del menu: OCULTO a pedido (pagina inutil) */
      '<li><a href="contact.html"' + act("contacto") + ">Contacto</a></li>" +
      '</ul><i class="mobile-nav-toggle d-xl-none bi bi-list"></i></nav>' +
      '<div class="jfz-actions">' +   /* (lupa de busqueda eliminada a pedido: ya no se muestra en el header) */
      '<a class="jfz-cart-link" href="carrito.html" aria-label="Carrito de compras"><i class="bi bi-cart3"></i><span class="jfz-badge" id="jfz-badge">0</span></a>' +
      '<button type="button" id="jfz-auth" class="jfz-auth"></button></div></div>';
    var f = $("#footer");
    if (f) {
      var soc = [["INSTAGRAM", "bi-instagram"], ["TIKTOK", "bi-tiktok"], ["FACEBOOK", "bi-facebook"], ["YOUTUBE", "bi-youtube"]]
        .filter(function (x) { return C[x[0]]; })
        .map(function (x) { return '<a href="' + C[x[0]] + '" target="_blank" rel="noopener" aria-label="' + x[0] + '"><i class="bi ' + x[1] + '"></i></a>'; }).join("");
      f.innerHTML = '<div class="container"><div class="copyright text-center"><p>© <span>Copyright</span> <strong class="px-1 sitename">JuanetoFZ</strong> <span>Todos los derechos reservados</span></p></div>' +
        '<div class="social-links d-flex justify-content-center">' + soc + "</div>" +
        /* Pie: enlace a Herramientas OCULTO a pedido */
        '<div class="credits">Diseñado por <a href="https://bootstrapmade.com/">BootstrapMade</a></div></div>';
    }
    $$("[data-cfg]").forEach(function (el) { var k = el.getAttribute("data-cfg"); if (C[k]) el.textContent = C[k]; });
    var a = $("#jfz-auth"); if (a) a.addEventListener("click", function () { user ? logout() : login(); });
    refreshAuthUI();
  }

  /* ---------- sesión (Google / modo prueba) ---------- */
  function refreshAuthUI() {
    var a = $("#jfz-auth"); if (!a) return;
    if (user) { a.innerHTML = '<i class="bi bi-person-check"></i> <span>' + esc((user.name || "Cuenta").split(" ")[0]) + " · Salir</span>"; a.title = user.email || ""; }
    else a.innerHTML = '<i class="bi bi-google"></i> <span>Iniciar sesión</span>';
  }
  function setUser(u) {
    user = u; cart = [];
    if (u) { try { cart = JSON.parse(localStorage.getItem("jfz_cart_" + u.uid) || "[]").filter(valid); } catch (e) { cart = []; } }
    refreshAuthUI();
    if (u && pending) { var f = pending; pending = null; add(f); }
    syncCart();
  }
  function saveCart() { if (user) localStorage.setItem("jfz_cart_" + user.uid, JSON.stringify(cart)); }
  function login() {
    if (demo) {
      var n = prompt("MODO PRUEBA (sin Google todavía).\nEscribe tu nombre para simular el inicio de sesión:", "Cliente de prueba");
      if (!n) { pending = null; return; }
      var u = { uid: "demo", name: n, email: "prueba@ejemplo.com" };
      localStorage.setItem("jfz_demo_user", JSON.stringify(u)); setUser(u); return;
    }
    if (!auth) { toast("Cargando inicio de sesión… intenta de nuevo."); return; }
    fb.signInWithPopup(auth, new fb.GoogleAuthProvider()).catch(function (e) {
      pending = null; toast(e && e.code === "auth/unauthorized-domain" ? "Dominio no autorizado en Firebase." : "No se pudo iniciar sesión.");
    });
  }
  function logout() {
    if (demo) { localStorage.removeItem("jfz_demo_user"); setUser(null); return; }
    fb.signOut(auth);
  }
  function initAuth() {
    if (demo) { try { setUser(JSON.parse(localStorage.getItem("jfz_demo_user") || "null")); } catch (e) { setUser(null); } return; }
    var v = "https://www.gstatic.com/firebasejs/12.12.0/";
    Promise.all([import(v + "firebase-app.js"), import(v + "firebase-auth.js")]).then(function (m) {
      var app = m[0].initializeApp(C.FIREBASE);
      fb = m[1]; auth = fb.getAuth(app);
      fb.onAuthStateChanged(auth, function (u) {
        setUser(u ? { uid: u.uid, name: u.displayName || "", email: u.email || "", photo: u.photoURL || "" } : null);
      });
    }).catch(function () { toast("No se pudo cargar Firebase. Revisa tu conexión."); });
  }

  /* ---------- carrito ---------- */
  function has(f) { return cart.indexOf(f) > -1; }
  function add(f) {
    if (!user) { pending = f; toast("Inicia sesión con Google para continuar"); login(); return; }
    if (!has(f)) {
      cart.push(f); saveCart(); toast(label(f) + " agregado al carrito");
      if (isSvc(f) && svc(f).aviso) showModal(C.AVISO_SESION);
    }
    syncCart();
  }
  function remove(f) { cart = cart.filter(function (x) { return x !== f; }); saveCart(); syncCart(); }
  function clearCart() { cart = []; saveCart(); syncCart(); }
  function toggle(f) { has(f) ? remove(f) : add(f); }
  function syncCart() {
    var b = $("#jfz-badge"); if (b) { b.textContent = cart.length; b.style.display = cart.length ? "" : "none"; }
    $$(".jfz-add").forEach(function (btn) {
      var on = has(btn.getAttribute("data-f"));
      btn.classList.toggle("on", on);
      btn.innerHTML = on ? '<i class="bi bi-check-lg"></i><span class="txt">En el carrito</span>' : '<i class="bi bi-cart-plus"></i><span class="txt">Agregar</span>';
      btn.title = on ? "En el carrito" : "Agregar";
      var fig = btn.closest(".jfz-card"); if (fig) fig.classList.toggle("is-selected", on);
    });
    $$(".jfz-svc-add").forEach(function (btn) {
      var on = has("svc:" + btn.getAttribute("data-s"));
      btn.classList.toggle("on", on);
      btn.innerHTML = on ? '<i class="bi bi-check-lg"></i> En el carrito' : '<i class="bi bi-cart-plus"></i> Agregar al carrito';
    });
    renderCartPage();
  }

  /* ---------- galería + filtros (fechas, trimestres, orden) ---------- */
  var EST = { q: "", etiquetas: [], desde: "", hasta: "", trim: [], orden: "" };
  /* Paginado de la galería: NO se pintan todas las fotos de golpe. Al inicio y cada vez
     que el usuario pulsa «Cargar más imágenes» se agregan LOTE fotos a la vez.
     El tope antiguo (LIMITE_SECCION = 300) era el culpable de que la página «se cortara»
     en la imagen ~3036: todo lo que pasara de ese número simplemente no se renderizaba. */
  var LOTE = 50;                 // fotos por lote (recomendado: equilibrio entre rapidez y peso)
  var topePorSeccion = {};       // id de sección -> cuántas fotos visibles están pintadas
  function resetTope() { topePorSeccion = {}; }
  /* A pedido del dueño del sitio:
     - La barra de búsqueda quedó ELIMINADA del código (ya no existe en la galería).
     - Las etiquetas "motos", "caras" y "cascos" quedaron BORRADAS: no se muestran
       como botones de filtro ni como chips, aunque sigan escritas en fotos.js.
     Filtros disponibles ahora: fecha desde/hasta, trimestres y orden por fecha.
     El panel es plegable hacia abajo y se pega bajo el menú al hacer scroll (ver galeria-plus.css). */
  var ETIQUETAS_PROHIBIDAS = ["motos", "caras", "cascos"];   // borradas de la vista (a pedido)
  function etiquetaVisible(e) { return ETIQUETAS_PROHIBIDAS.indexOf(String(e).toLowerCase()) < 0; }
  var ETIQUETAS_SITIO = [];   // vacio a proposito: los botones de etiquetas no se pintan
  function fechaDe(s, f) { return (s.fechas && s.fechas[f]) || ""; }
  function trimestreDe(fecha) { if (!fecha) return ""; var p = fecha.split("-"); return p[0] + "-T" + (Math.floor((+p[1] - 1) / 3) + 1); }
  function textoBusca(s, f) { var e = (s.etiquetas && s.etiquetas[f]) || []; return (base(f) + " " + s.titulo + " " + e.join(" ") + " " + fechaDe(s, f)).toLowerCase(); }

  function pasaFiltro(s, f) {
    if (EST.etiquetas.length) { var e = (s.etiquetas && s.etiquetas[f]) || []; for (var j = 0; j < EST.etiquetas.length; j++) if (e.indexOf(EST.etiquetas[j]) < 0) return false; }
    var d = fechaDe(s, f);
    if (EST.desde && (!d || d < EST.desde)) return false;
    if (EST.hasta && (!d || d > EST.hasta)) return false;
    if (EST.trim.length && EST.trim.indexOf(trimestreDe(d)) < 0) return false;
    return true;
  }
  function hayFiltros() { return !!(EST.etiquetas.length || EST.desde || EST.hasta || EST.trim.length || EST.orden); }
  function chipHTML(txt, accion, val) { return '<span class="jfz-chip">' + esc(txt) + '<button type="button" data-acc="' + accion + '" data-v="' + esc(val || "") + '" aria-label="Quitar filtro"><i class="bi bi-x-lg"></i></button></span>'; }
  /* Formatea "2026-08-27" como "27 ago 2026" (para cajas de fecha legibles y cortas) */
  var MESES_ABREV = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  function fechaCorta(d) { var p = String(d).split("-"); return p.length === 3 ? (+p[2]) + " " + MESES_ABREV[+p[1] - 1] + " " + p[0] : d; }
  function renderChips(box) {
    /* se llama a veces con el panel ya re-pintado (p. ej. tras «Limpiar todo»): si no se le
       pasa la caja y el id no está en el DOM, salir sin errores en vez de lanzar TypeError */
    box = box || $("#jfz-filtros-activos"); if (!box) return;
    var c = [];
    EST.etiquetas.forEach(function (e) { if (etiquetaVisible(e)) c.push(chipHTML("#" + e, "tag", e)); });
    if (EST.desde) c.push(chipHTML("desde " + EST.desde, "desde"));
    if (EST.hasta) c.push(chipHTML("hasta " + EST.hasta, "hasta"));
    EST.trim.forEach(function (t) { c.push(chipHTML(t, "trim", t)); });
    if (EST.orden) c.push(chipHTML(EST.orden === "asc" ? "fecha ↑ antiguas primero" : "fecha ↓ nuevas primero", "orden"));
    box.innerHTML = c.length ? c.join("") + '<button type="button" class="jfz-limpiar" data-acc="limpiar"><i class="bi bi-arrow-counterclockwise"></i> Limpiar todo</button>' : "";
    box.hidden = !c.length;
    /* el panel puede haber crecido (o encogido) al cambiar los chips: re-medir el cuerpo abierto */
    var cuerpoC = $("#jfz-filtros-cuerpo"), panelC = $("#jfz-buscador");
    if (cuerpoC && panelC && panelC.classList.contains("abierto")) cuerpoC.style.maxHeight = cuerpoC.scrollHeight + "px";
  }
  function trimsDelSitio() {
    var trims = {};
    S.forEach(function (s) { s.fotos.forEach(function (f) { var t = trimestreDe(fechaDe(s, f)); if (t) trims[t] = 1; }); });
    return Object.keys(trims).sort();
  }
  function buscadorHTML() {
    if (!S.length) return "";   // sin fotos no hay filtros que mostrar
    var listaTrims = trimsDelSitio();
    /* Panel de filtros: barra superior siempre visible + cuerpo plegable hacia abajo.
       La barra de busqueda y las etiquetas motos/caras/cascos fueron eliminadas a pedido. */
    return '<div class="jfz-buscador jfz-filtros" id="jfz-buscador">' +
      '<button type="button" class="jfz-filtros-toggle" id="jfz-filtros-toggle" aria-expanded="false" aria-controls="jfz-filtros-cuerpo">' +
        '<span class="jfz-ft-ico"><i class="bi bi-sliders"></i></span>' +
        '<span class="jfz-ft-txt">Filtros</span>' +
        '<span class="jfz-ft-resumen" id="jfz-ft-resumen"></span>' +
        '<span class="jfz-ft-flecha"><i class="bi bi-chevron-down"></i></span>' +
      '</button>' +
      '<div class="jfz-filtros-cuerpo" id="jfz-filtros-cuerpo">' +
        '<div class="jfz-filtro-grupo jfz-fg-fechas">' +
          '<span class="jfz-fg-titulo"><i class="bi bi-calendar-range"></i> Fechas</span>' +
          '<div class="jfz-fg-campos">' +
            '<label>Desde <input type="date" id="jfz-desde" value="' + esc(EST.desde) + '" title="Fecha mínima"></label>' +
            '<label>Hasta <input type="date" id="jfz-hasta" value="' + esc(EST.hasta) + '" title="Fecha máxima"></label>' +
          '</div>' +
        '</div>' +
        (listaTrims.length ?
        '<div class="jfz-filtro-grupo jfz-fg-trims">' +
          '<span class="jfz-fg-titulo"><i class="bi bi-calendar3"></i> Trimestres</span>' +
          '<div class="jfz-fg-campos jfz-trims">' + listaTrims.map(function (t) { return '<label class="jfz-trim' + (EST.trim.indexOf(t) >= 0 ? " on" : "") + '"><input type="checkbox" value="' + t + '"' + (EST.trim.indexOf(t) >= 0 ? " checked" : "") + '> ' + t + '</label>'; }).join("") + '</div>' +
        '</div>' : "") +
        '<div class="jfz-filtro-grupo jfz-fg-orden">' +
          '<span class="jfz-fg-titulo"><i class="bi bi-sort-down"></i> Orden</span>' +
          '<div class="jfz-fg-campos">' +
            '<select id="jfz-orden"><option value="">Sin orden especial</option><option value="desc"' + (EST.orden === "desc" ? " selected" : "") + '>Fecha: nuevas primero</option><option value="asc"' + (EST.orden === "asc" ? " selected" : "") + '>Fecha: antiguas primero</option></select>' +
          '</div>' +
        '</div>' +
        '<div class="jfz-filtros-activos" id="jfz-filtros-activos" hidden></div>' +
        '<div class="jfz-contador" id="jfz-contador"></div>' +
      '</div>' +
    "</div>";
  }

  function cardHTML(f, grupo, carpeta) {
    var n = base(f);
    return '<div class="col-xl-3 col-lg-4 col-md-6"><figure class="jfz-card">' +
      '<a href="' + ruta(f, carpeta) + '" class="jfz-lightbox" data-gallery="' + grupo + '" title="' + n + '"><img loading="lazy" src="' + ruta(f, carpeta) + '" alt="Foto ' + n + '"></a>' +
      '<figcaption><span>' + n + '</span><button type="button" class="jfz-add" data-f="' + f + '"></button></figcaption></figure></div>';
  }
  function wireAdd(root) {
    $$(".jfz-add", root).forEach(function (b) { b.addEventListener("click", function () { toggle(b.getAttribute("data-f")); }); });
  }
  function initLightbox(sel) {
    if (typeof GLightbox === "undefined") return;
    if (lightbox) { try { lightbox.destroy(); } catch (e) {} }
    lightbox = GLightbox({ selector: sel || ".jfz-lightbox" });
  }
  /* Título que se pinta en la pestaña/sección: si la única sección se llama igual
     que la página («Galería»), no tiene sentido repetir ese cartel: se ve "Fotos". */
  function tituloDeSeccion(s) {
    var esGaleria = function (x) { return String(x).trim().toLowerCase() === "galeria"; };
    if (esGaleria(s.titulo) && (S.length <= 1 || esGaleria(s.id))) return "Fotos";
    return s.titulo;
  }
  function renderGallery() {
    var box = $("#jfz-galeria"); if (!box) return;
    var tabs = $("#jfz-tabs");
    tabs.innerHTML = '<button type="button" data-id="todos">Todos</button>' + S.map(function (s) { return '<button type="button" data-id="' + s.id + '">' + esc(tituloDeSeccion(s)) + "</button>"; }).join("");
    box.innerHTML = buscadorHTML() + S.map(function (s) {
      return '<section class="jfz-sec" data-id="' + s.id + '" id="sec-' + s.id + '"><h2 class="jfz-sec-title jfz-scroll-espia">' + esc(tituloDeSeccion(s)) + ' <small>' + s.fotos.length + " fotos</small></h2>" +
        '<div class="row gy-4"></div></section>';
    }).join("");
    wireBuscador(box);
    pintarGaleria();
    tabs.addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) location.hash = b.getAttribute("data-id"); });
    window.addEventListener("hashchange", showTab);
    if (location.hash === "#buscar") { setTimeout(function () { var bq = $("#jfz-q"); if (bq) { try { bq.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {} bq.focus({ preventScroll: true }); } }, 80); }
    showTab(); syncCart();
  }
  /* Pinta las tarjetas que pasan los filtros, sección por sección, pero SOLO hasta el
     tope de paginado (topePorSeccion). El resto queda detrás del botón «Cargar más
     imágenes»; si aún falta material por pintar se muestra una animación de carga abajo. */
  function pintarGaleria() {
    resetTope();                 // al cambiar filtros/orden el paginado vuelve a empezar desde 0
    var box = $("#jfz-galeria"); if (!box) return;
    var total = 0, pendientesTotales = 0;
    $$(".jfz-sec").forEach(function (secEl) {
      var id = secEl.getAttribute("data-id");
      var s = S.filter(function (x) { return x.id === id; })[0];
      if (!s) return;
      var visibles = s.fotos.filter(function (f) { return pasaFiltro(s, f); });
      if (EST.orden) visibles.sort(function (a, b) {
        var da = fechaDe(s, a), db = fechaDe(s, b);
        if (!da && !db) return a < b ? -1 : 1;
        if (!da) return 1; if (!db) return -1;
        return EST.orden === "asc" ? (da < db ? -1 : da > db ? 1 : (a < b ? -1 : 1)) : (da > db ? -1 : da < db ? 1 : (a < b ? -1 : 1));
      });
      topePorSeccion[id] = Math.min(LOTE, visibles.length);
      total += visibles.length;
      pendientesTotales += Math.max(0, visibles.length - LOTE);
      var fila = secEl.querySelector(".row");
      fila.classList.add("jfz-mosaico");   // conserva el mosaico del CSS sin romper la animación plegable
      fila.innerHTML = visibles.length ? visibles.slice(0, topePorSeccion[id]).map(function (f) { return cardHTML(f, id, s.carpeta); }).join("") :
        (hayFiltros() ? "" : '<p class="jfz-empty">' + (s.fotos.length ? "Ninguna foto con esos filtros." : "Próximamente: todavía no hay fotos en <code>fotos/" + esc(s.carpeta) + "/</code>. Ejecuta herramientas/actualizacion_definitiva.bat.") + "</p>");
      secEl.hidden = !(visibles.length || !hayFiltros());
      var small = secEl.querySelector(".jfz-sec-title small");
      if (small) small.textContent = hayFiltros() ? visibles.length + " de " + s.fotos.length + " fotos" : s.fotos.length + " fotos";
    });
    var cont = $("#jfz-contador");
    if (cont) cont.textContent = hayFiltros() ? (total ? total + (total === 1 ? " foto encontrada" : " fotos encontradas") : "Sin resultados con esos filtros") : "";
    renderChips();
    actualizarResumenFiltros();
    /* si el panel esta abierto, se vuelve a medir para que la animacion plegable no corte el contenido */
    var cuerpoF = $("#jfz-filtros-cuerpo"), panelF = $("#jfz-buscador");
    if (cuerpoF && panelF && panelF.classList.contains("abierto")) cuerpoF.style.maxHeight = cuerpoF.scrollHeight + "px";
    wireAdd(box_galeria());
    initLightbox(".jfz-sec:not([hidden]) .jfz-lightbox");
    renderFooterLoad(pendientesTotales);
    try { window.dispatchEvent(new Event("jfz-gallery-painted")); } catch (e) {}
  }
  function box_galeria() { return $("#jfz-galeria"); }

  /* ---------- paginado: pie con botón «Cargar más imágenes» + spinner de carga ---------- */
  function renderFooterLoad(pendientes) {
    var box = box_galeria(); if (!box) return;
    var foot = $("#jfz-load-more");
    if (!foot) {
      foot = document.createElement("div");
      foot.id = "jfz-load-more";
      foot.className = "jfz-load-more";
      foot.innerHTML =
        '<button type="button" class="jfz-btn-mas" id="jfz-btn-mas"><i class="bi bi-collection"></i> Cargar más imágenes</button>' +
        '<div class="jfz-cargando" id="jfz-cargando" hidden><span class="jfz-spinner" aria-hidden="true"></span> Cargando imágenes…</div>' +
        '<div class="jfz-fin" id="jfz-fin" hidden><i class="bi bi-check2-circle"></i> Has visto todas las imágenes</div>';
      box.appendChild(foot);
      $("#jfz-btn-mas", foot).addEventListener("click", cargarMas);
    }
    var btn = $("#jfz-btn-mas", foot), fin = $("#jfz-fin", foot);
    if (pendientes > 0) {
      btn.hidden = false; fin.hidden = true;
      btn.innerHTML = '<i class="bi bi-collection"></i> Cargar más imágenes <small>(quedan ' + pendientes + ')</small>';
    } else {
      btn.hidden = true;
      fin.hidden = !(box.querySelector(".jfz-card"));  // «fin» solo si realmente hay fotos pintadas
    }
    $("#jfz-cargando", foot).hidden = true;
  }
  /* Carga un lote más por cada sección visible y lo ANIMA en pantalla (fade-in suave).
     Se muestra el spinner mientras el navegador decodifica las nuevas imágenes; cuando
     terminan de cargarse (o tras un tiempo máximo de seguridad) se oculta y reaparece
     el botón, listo para cargar otro lote si aún faltan. */
  function cargarMas() {
    var btn = $("#jfz-btn-mas"), spin = $("#jfz-cargando");
    if (btn) btn.hidden = true;
    if (spin) spin.hidden = false;
    var nuevosImgs = [];
    $$(".jfz-sec:not([hidden])").forEach(function (secEl) {
      var id = secEl.getAttribute("data-id");
      var s = S.filter(function (x) { return x.id === id; })[0];
      if (!s) return;
      var visibles = s.fotos.filter(function (f) { return pasaFiltro(s, f); });
      if (EST.orden) visibles.sort(function (a, b) {
        var da = fechaDe(s, a), db = fechaDe(s, b);
        if (!da && !db) return a < b ? -1 : 1;
        if (!da) return 1; if (!db) return -1;
        return EST.orden === "asc" ? (da < db ? -1 : da > db ? 1 : (a < b ? -1 : 1)) : (da > db ? -1 : da < db ? 1 : (a < b ? -1 : 1));
      });
      var prev = topePorSeccion[id] || 0;
      var nuevo = Math.min(prev + LOTE, visibles.length);
      if (nuevo <= prev) return;
      topePorSeccion[id] = nuevo;
      var fila = secEl.querySelector(".row");
      /* si el filtro dejó la sección sin fotos, quita el aviso de vacío antes de agregar tarjetas */
      var vacio = fila.querySelector(".jfz-empty"); if (vacio) vacio.remove();
      var frag = document.createElement("div");
      frag.innerHTML = visibles.slice(prev, nuevo).map(function (f) { return cardHTML(f, id, s.carpeta); }).join("");
      var added = Array.prototype.slice.call(frag.children);
      added.forEach(function (el) { el.classList.add("jfz-nueva"); fila.appendChild(el); });
      nuevosImgs = nuevosImgs.concat(added);
      /* dispara la transición de entrada en el siguiente frame */
      requestAnimationFrame(function () { added.forEach(function (el) { el.classList.add("mostrar"); }); });
    });
    wireAdd($("#jfz-galeria"));
    syncCart();
    initLightbox(".jfz-sec:not([hidden]) .jfz-lightbox");
    try { window.dispatchEvent(new Event("jfz-gallery-painted")); } catch (e) {}
    /* esperar a que carguen las imágenes nuevas (con tope de 4 s por seguridad) */
    var pendientesImg = nuevosImgs.reduce(function (n, el) { var im = el.querySelector("img"); return n + (im && !im.complete ? 1 : 0); }, 0);
    var terminado = false;
    function listo() {
      if (terminado) return; terminado = true;
      nuevosImgs.forEach(function (el) { setTimeout(function () { el.classList.remove("jfz-nueva"); }, 50); });
      var pend = 0;
      $$(".jfz-sec:not([hidden])").forEach(function (secEl) {
        var id = secEl.getAttribute("data-id");
        var s = S.filter(function (x) { return x.id === id; })[0];
        if (!s) return;
        var visibles = s.fotos.filter(function (f) { return pasaFiltro(s, f); });
        pend += Math.max(0, visibles.length - (topePorSeccion[id] || 0));
      });
      renderFooterLoad(pend);
    }
    if (!pendientesImg) { setTimeout(listo, 350); }   // todo cacheado: dejar ver la animación un instante
    else {
      nuevosImgs.forEach(function (el) {
        var im = el.querySelector("img"); if (!im || im.complete) return;
        im.addEventListener("load", function () { if (--pendientesImg <= 0) listo(); });
        im.addEventListener("error", function () { if (--pendientesImg <= 0) listo(); });
      });
      setTimeout(listo, 4000);
    }
  }

  /* Resumen corto que se ve en la barra de filtros cuando el panel esta plegado.
     Cada filtro activo se muestra en su PROPIA cajita (ya no una sola píldora larga
     con todo concatenado). El contenedor permite flex-wrap para que, en pantallas
     estrechas, las cajitas se amontenen de arriba hacia abajo de forma estética. */
  function actualizarResumenFiltros() {
    var r = $("#jfz-ft-resumen"); if (!r) return;
    var chipsR = [];
    if (EST.desde || EST.hasta) chipsR.push('<span class="jfz-ft-caja"><i class="bi bi-calendar-range"></i>' + esc(((EST.desde ? fechaCorta(EST.desde) : "…") + " → " + (EST.hasta ? fechaCorta(EST.hasta) : "…"))) + '</span>');
    if (EST.trim.length === 1) chipsR.push('<span class="jfz-ft-caja"><i class="bi bi-calendar3"></i>' + esc(EST.trim[0]) + '</span>');
    else if (EST.trim.length > 1) chipsR.push('<span class="jfz-ft-caja"><i class="bi bi-calendar3"></i>' + esc(EST.trim.join(", ")) + '</span>');
    if (EST.orden) chipsR.push('<span class="jfz-ft-caja"><i class="bi bi-sort-' + (EST.orden === "asc" ? "down-alt" : "down") + '"></i>' + (EST.orden === "asc" ? "↑ antiguas" : "↓ nuevas") + '</span>');
    r.innerHTML = chipsR.join("");
    r.hidden = !chipsR.length;
    var panel = $("#jfz-buscador"); if (panel) panel.classList.toggle("tiene-filtros", chipsR.length > 0);
  }

  /* Plegable hacia abajo: la barra "Filtros" siempre visible; el cuerpo sube/baja con animación */
  function toggleFiltros(forzar) {
    var panel = $("#jfz-buscador"), cuerpo = $("#jfz-filtros-cuerpo"), tog = $("#jfz-filtros-toggle");
    if (!panel || !cuerpo || !tog) return;
    var abierto = typeof forzar === "boolean" ? forzar : !panel.classList.contains("abierto");
    tog.setAttribute("aria-expanded", abierto ? "true" : "false");
    if (abierto) {
      panel.classList.add("abierto");
      cuerpo.style.maxHeight = cuerpo.scrollHeight + "px";
    } else {
      cuerpo.style.maxHeight = cuerpo.scrollHeight + "px";   // fuerza el alto actual para poder animar hacia abajo
      void cuerpo.offsetHeight;                              // reflow para que el navegador registre el alto
      panel.classList.remove("abierto");
      cuerpo.style.maxHeight = "0px";
    }
  }
  function wireBuscador(root) {
    var d1 = $("#jfz-desde", root), d2 = $("#jfz-hasta", root), o = $("#jfz-orden", root);
    var tog = $("#jfz-filtros-toggle", root);
    if (tog) tog.addEventListener("click", function () { toggleFiltros(); });
    if (d1) d1.addEventListener("change", function () { EST.desde = d1.value; pintarGaleria(); });
    if (d2) d2.addEventListener("change", function () { EST.hasta = d2.value; pintarGaleria(); });
    if (o) o.addEventListener("change", function () { EST.orden = o.value; pintarGaleria(); });
    $$(".jfz-tag", root).forEach(function (b) { b.addEventListener("click", function () {
      var t = b.getAttribute("data-t"), i = EST.etiquetas.indexOf(t);
      i >= 0 ? EST.etiquetas.splice(i, 1) : EST.etiquetas.push(t);
      b.classList.toggle("on", i < 0);
      pintarGaleria();
    }); });
    $$("input[type=checkbox]", $(".jfz-trims", root) || root).forEach(function (cb) { cb.addEventListener("change", function () {
      var t = cb.value, i = EST.trim.indexOf(t);
      i >= 0 ? EST.trim.splice(i, 1) : EST.trim.push(t);
      cb.closest(".jfz-trim").classList.toggle("on", i < 0);
      pintarGaleria();
    }); });
    var chips = $("#jfz-filtros-activos", root);
    if (chips) chips.addEventListener("click", function (e) {
      var b = e.target.closest("[data-acc]"); if (!b) return;
      var acc = b.getAttribute("data-acc"), v = b.getAttribute("data-v");
      if (acc === "tag") { EST.etiquetas = EST.etiquetas.filter(function (x) { return x !== v; }); var tb = $('.jfz-tag[data-t="' + v + '"]'); if (tb) tb.classList.remove("on"); }
      if (acc === "desde") { EST.desde = ""; if (d1) d1.value = ""; }
      if (acc === "hasta") { EST.hasta = ""; if (d2) d2.value = ""; }
      if (acc === "trim") { EST.trim = EST.trim.filter(function (x) { return x !== v; }); var cb2 = $('.jfz-trims input[value="' + v + '"]'); if (cb2) { cb2.checked = false; if (cb2.closest(".jfz-trim")) cb2.closest(".jfz-trim").classList.remove("on"); } }
      if (acc === "orden") { EST.orden = ""; if (o) o.value = ""; }
      if (acc === "limpiar") {
        EST = { q: "", etiquetas: [], desde: "", hasta: "", trim: [], orden: "" };
        /* Se re-pinta SOLO el panel de filtros para que los controles vuelvan a su estado
           vacío; como el DOM del panel se sustituye, los chips y el resumen se actualizan
           apuntando directamente a la caja nueva (antes, al llamar renderGallery() completo,
           se duplicaban listeners en las pestañas y quedaban referencias colgadas). */
        var boxL = $("#jfz-galeria"), panelViejo = $("#jfz-buscador");
        if (boxL && panelViejo) {
          var tmp = document.createElement("div");
          tmp.innerHTML = buscadorHTML();
          var panelNuevo = tmp.firstChild;
          if (panelNuevo) boxL.replaceChild(panelNuevo, panelViejo);
          wireBuscador(boxL);
          renderChips($("#jfz-filtros-activos"));
          actualizarResumenFiltros();
        }
        pintarGaleria();
        return;
      }
      pintarGaleria();
    });
  }
  function showTab() {
    var id = (location.hash || "").replace("#", ""); if (id !== "todos" && !S.some(function (s) { return s.id === id; })) id = "todos";
    $$(".jfz-sec").forEach(function (s) { s.hidden = !(id === "todos" || s.getAttribute("data-id") === id); });
    $$("#jfz-tabs button").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-id") === id); });
    initLightbox(".jfz-sec:not([hidden]) .jfz-lightbox");
    window.scrollTo({ top: 0 });
  }
  function renderFeatured() {
    var box = $("#jfz-destacadas"); if (!box) return;
    /* Destacadas: se recorre de la sección MÁS NUEVA a la más antigua (la última del
       listado es la que se actualiza primero), y se toman fotos reales aunque alguna
       sección venga vacía. Antes solo miraba la última y, si estaba vacía, no salía nada. */
    var all = [];
    for (var i = S.length - 1; i >= 0 && all.length < 8; i--) {
      var s = S[i];
      for (var j = 0; j < s.fotos.length && all.length < 8; j++) all.push({ f: s.fotos[j], carpeta: s.carpeta });
    }
    box.innerHTML = all.map(function (x) { return cardHTML(x.f, "inicio", x.carpeta); }).join("");
    wireAdd(box); initLightbox(); syncCart();
  }

  /* ---------- página del carrito ---------- */
  function compact(files) {
    var nums = files.map(function (f) { var m = f.match(/^IMG_(\d+)\.(?:jpe?g|png|webp)$/i); return m ? +m[1] : null; });
    if (nums.some(function (n) { return n === null; })) return files.join(", ");
    nums.sort(function (a, b) { return a - b; });
    var out = [], s = nums[0], p = s;
    for (var i = 1; i <= nums.length; i++) {
      if (nums[i] === p + 1) { p = nums[i]; continue; }
      out.push(s === p ? "IMG_" + s : "IMG_" + s + " a IMG_" + p); s = nums[i]; p = nums[i];
    }
    return out.join(", ");
  }
  function totals() {
    var n = photos().length, u = unit(n), sv = 0, conv = false;
    svcs().forEach(function (s) { if (typeof s.precio === "number") sv += s.precio; else conv = true; });
    return { n: n, u: u, fotos: n * u, sv: sv, conv: conv, total: n * u + sv };
  }
  function precioSvc(s) { return typeof s.precio === "number" ? money(s.precio) : "A convenir"; }
  function sendWhatsApp() {
    if (!cart.length) return;
    if (/X/i.test(C.WHATSAPP)) { alert("Falta configurar el número de WhatsApp en assets/js/config.js"); return; }
    // El mensaje ya incluye el comando PowerShell dentro del texto: el dueño solo lo
    // copia desde el chat y lo pega en una consola. Si la URL queda muy larga para
    // wa.me, se pasa a modo compacto (sin el comando) y se ofrece descargar el .ps1.
    var url = "https://wa.me/" + C.WHATSAPP + "?text=" + encodeURIComponent(buildMessage(false));
    if (url.length > 1900) {
      url = "https://wa.me/" + C.WHATSAPP + "?text=" + encodeURIComponent(buildMessage(true));
      toast("Pedido muy largo: el comando PowerShell no cabe en WhatsApp — usa el botón «Descargar pedido (.ps1)»");
    }
    window.open(url, "_blank", "noopener");
  }

  /* ---------- pedido: script PowerShell que copia los ORIGINALES del carrito ---------- */
  // El sitio solo publica WebP; los RAW/CR2/JPG originales viven en tu PC dentro de por-procesar/.
  // El comando PowerShell se arma con los nombres EXACTOS del carrito y viaja DENTRO del
  // mensaje de WhatsApp: el dueño solo copia el bloque y lo pega en una consola PowerShell.
  // Para pegar en PowerShell sin errores, el comando usa SOLO comillas dobles (los nombres
  // de archivo nunca llevan "), no lleva backticks ni llaves ${} (WhatsApp los come como
  // emojis) y evita los guiones bajos (Word Autocorrector los convierte en espacios al copiar).
  function psCmd() {
    var nombres = photos().map(base);
    if (!nombres.length) return "";
    var L = [];
    L.push("# Pedido JFZ " + new Date().toISOString().slice(0, 10) + " - copia los ORIGINALES (RAW/CR2/JPG) del carrito a una carpeta de entrega");
    L.push("$orig = Read-Host 'Ruta de la carpeta de originales (ej. C:\\Users\\TuUsuario\\Pictures\\" + ORIGINALES + ")'");
    L.push("$dest = Join-Path $orig ('pedido-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))");
    L.push("New-Item -ItemType Directory -Force -Path $dest | Out-Null");
    L.push("$lista = @(" + nombres.map(function (n) { return '"' + n + '"'; }).join(", ") + ")");
    L.push("$ok = 0; $faltan = @()");
    L.push("foreach ($n in $lista) {");
    L.push("  $hit = Get-ChildItem -LiteralPath $orig -Recurse -File | Where-Object { $_.BaseName -ieq $n } | Select-Object -First 1");
    L.push("  if ($hit) { Copy-Item -LiteralPath $hit.FullName -Destination $dest -Force; $ok++; Write-Host ('OK   ' + $n + ' -> ' + $hit.Name) -ForegroundColor Green }");
    L.push("  else { $faltan += $n; Write-Host ('FALTA ' + $n) -ForegroundColor Yellow }");
    L.push("}");
    L.push("Write-Host ('Copiados: ' + $ok + ' -> ' + $dest)");
    L.push("if ($faltan.Count) { Write-Host ('Faltaron: ' + ($faltan -join ', ')) -ForegroundColor Yellow }");
    L.push("explorer $dest");
    return L.join("\n");
  }
  function buildMessage(compactMode) {
    var t = totals(), ph = photos(), sv = svcs();
    // En modo compacto (pedidos muy largos que no caben en la URL de wa.me) se
    // omiten TODAS las fotos y el comando PowerShell: el comprador solo pone el
    // rango y el .ps1 de descarga queda como respaldo.
    if (compactMode) {
      var Lc = ["Hola Juaneto 👋 Quiero hacer este pedido:", "", "Nombre: " + (user.name || "-"), "Correo: " + (user.email || "-"), ""];
      if (ph.length) Lc.push("FOTOS (" + ph.length + "): " + compact(ph), "");
      if (sv.length) {
        Lc.push("SERVICIOS:");
        sv.forEach(function (s) { Lc.push("- " + s.nombre + " (" + (typeof s.precio === "number" ? money(s.precio) : "precio a convenir") + ")"); });
        Lc.push("");
      }
      if (ph.length) Lc.push("Fotos: " + t.n + " x " + money(t.u) + " = " + money(t.fotos));
      Lc.push("Total: " + money(t.total) + (t.conv ? " + servicios a convenir" : ""));
      if (sv.some(function (s) { return s.aviso; })) Lc.push("", "✔ Acepto las condiciones de las sesiones indicadas en el sitio.");
      return Lc.join("\n");
    }
    var L = ["Hola Juaneto 👋 Quiero hacer este pedido:", "", "Nombre: " + (user.name || "-"), "Correo: " + (user.email || "-"), ""];
    if (ph.length) {
      L.push("FOTOS (" + ph.length + "):");
      ph.forEach(function (f, i) { L.push((i + 1) + ". " + f); });
      L.push("");
    }
    if (sv.length) {
      L.push("SERVICIOS:");
      sv.forEach(function (s) { L.push("- " + s.nombre + " (" + (typeof s.precio === "number" ? money(s.precio) : "precio a convenir") + ")"); });
      L.push("");
    }
    if (ph.length) L.push("Fotos: " + t.n + " x " + money(t.u) + " = " + money(t.fotos));
    L.push("Total: " + money(t.total) + (t.conv ? " + servicios a convenir" : ""));
    if (sv.some(function (s) { return s.aviso; })) L.push("", "✔ Acepto las condiciones de las sesiones indicadas en el sitio.");
    if (ph.length) L.push("", "COMANDO POWERSHELL (copiar y pegar tal cual en una consola):", psCmd());
    return L.join("\n");
  }
  function renderCartPage() {
    var box = $("#jfz-carrito"); if (!box) return;
    if (!user) {
      box.innerHTML = '<div class="jfz-panel text-center"><h2>Inicia sesión para ver tu carrito</h2><p>Usa tu cuenta de Google para elegir fotos y servicios y enviar tu pedido.</p><button type="button" class="btn-get-started" id="jfz-login2">Iniciar sesión con Google</button>' + (demo ? '<p class="jfz-note">Modo prueba activo: el inicio de sesión es simulado.</p>' : "") + "</div>";
      $("#jfz-login2").addEventListener("click", login); return;
    }
    if (!cart.length) {
      box.innerHTML = '<div class="jfz-panel text-center"><h2>Tu carrito está vacío</h2><p>Hola, ' + esc((user.name || "").split(" ")[0]) + '. Elige tus fotos o tus servicios.</p><a class="btn-get-started" href="gallery.html">Ir a la galería</a> <a class="btn-get-started" href="services.html">Ver servicios</a></div>'; return;
    }
    var t = totals(), ph = photos();
    var rowsP = ph.map(function (f) {
      return '<div class="jfz-row"><img src="' + ruta(f) + '" alt=""><div class="jfz-row-n"><strong>' + base(f) + '</strong><span>' + f + '</span></div><span class="jfz-row-p">' + money(t.u) + '</span><button type="button" class="jfz-rm" data-f="' + f + '" aria-label="Quitar"><i class="bi bi-trash"></i></button></div>';
    }).join("");
    var rowsS = cart.filter(isSvc).map(function (x) {
      var s = svc(x);
      return '<div class="jfz-row"><i class="bi ' + (s.icono || "bi-stars") + ' jfz-row-i"></i><div class="jfz-row-n"><strong>' + esc(s.nombre) + '</strong><span>' + esc(s.nota || "") + '</span></div><span class="jfz-row-p">' + precioSvc(s) + '</span><button type="button" class="jfz-rm" data-f="' + x + '" aria-label="Quitar"><i class="bi bi-trash"></i></button></div>';
    }).join("");
    var aviso = svcs().some(function (s) { return s.aviso; }) ? '<div class="jfz-aviso-box"><i class="bi bi-exclamation-triangle"></i> ' + esc(C.AVISO_SESION) + "</div>" : "";
    box.innerHTML = '<div class="row gy-4"><div class="col-lg-8"><div class="jfz-panel"><h2>Tu pedido (' + cart.length + ')</h2>' + aviso +
      (rowsP ? '<h3 class="jfz-sub">Fotos</h3>' + rowsP : "") + (rowsS ? '<h3 class="jfz-sub">Servicios</h3>' + rowsS : "") +
      '</div></div><div class="col-lg-4"><div class="jfz-panel jfz-sum"><h2>Resumen</h2>' +
      (ph.length ? '<div class="jfz-line"><span>Fotos (' + t.n + ' x ' + money(t.u) + ')</span><span>' + money(t.fotos) + '</span></div>' : "") +
      (svcs().length ? '<div class="jfz-line"><span>Servicios</span><span>' + money(t.sv) + (t.conv ? " + a convenir" : "") + '</span></div>' : "") +
      '<div class="jfz-line jfz-total"><span>Total</span><span>' + money(t.total) + '</span></div>' +
      '<button type="button" class="btn-get-started w-100" id="jfz-send"><i class="bi bi-whatsapp"></i> Enviar pedido por WhatsApp</button>' +
      (ph.length ? '<p class="jfz-note">El comando <strong>PowerShell</strong> con los nombres exactos de estas fotos viaja dentro del mensaje de WhatsApp: solo cópialo y pégalo en una consola.</p>' : "") +
      '<button type="button" class="jfz-link" id="jfz-clear">Vaciar carrito</button>' +
      '<p class="jfz-note">El pago y la entrega se acuerdan por WhatsApp. Cuantas más fotos, menor el precio por foto.</p></div></div></div>';
    $$(".jfz-rm", box).forEach(function (b) { b.addEventListener("click", function () { remove(b.getAttribute("data-f")); }); });
    $("#jfz-send").addEventListener("click", sendWhatsApp);
    $("#jfz-clear").addEventListener("click", function () { if (confirm("¿Vaciar el carrito?")) clearCart(); });
  }

  /* ---------- servicios ---------- */
  function renderServices() {
    var box = $("#jfz-servicios"); if (!box) return;
    box.innerHTML = (C.SERVICIOS || []).map(function (s) {
      return '<div class="col-xl-4 col-md-6"><div class="jfz-serv"><i class="bi ' + (s.icono || "bi-stars") + '"></i><h3>' + esc(s.nombre) + '</h3>' +
        '<p class="jfz-serv-price">' + (typeof s.precio === "number" ? money(s.precio) : esc(s.precioTexto || "A convenir")) + '</p><p>' + esc(s.nota || "") + '</p>' +
        '<button type="button" class="jfz-svc-add" data-s="' + s.id + '"></button></div></div>';
    }).join("");
    $$(".jfz-svc-add", box).forEach(function (b) { b.addEventListener("click", function () { toggle("svc:" + b.getAttribute("data-s")); }); });
  }
  function showModal(msg) {
    var m = $("#jfz-modal");
    if (!m) {
      m = document.createElement("div"); m.id = "jfz-modal";
      m.innerHTML = '<div class="jfz-modal-box" role="dialog" aria-modal="true"><i class="bi bi-exclamation-triangle"></i><h3>Antes de continuar</h3><p id="jfz-modal-msg"></p><button type="button" class="btn-get-started" id="jfz-modal-ok">Entendido</button></div>';
      document.body.appendChild(m);
      $("#jfz-modal-ok").addEventListener("click", function () { m.hidden = true; });
      m.addEventListener("click", function (e) { if (e.target === m) m.hidden = true; });
    }
    $("#jfz-modal-msg").textContent = msg; m.hidden = false;
  }

  /* ---------- arranque ---------- */
  renderChrome();
  renderGallery();
  renderFeatured();
  renderServices();
  initAuth();
  syncCart();
  var pl = document.getElementById("preloader"); if (pl) pl.remove();
  if (demo && $("#jfz-demo-aviso")) $("#jfz-demo-aviso").hidden = false;

  /* Al cambiar el tamaño de la pantalla, si el panel de filtros esta abierto se
     re-mide su alto: al amontonarse los campos verticalmente el contenido crece y,
     sin esto, el max-height viejo cortaria parte de los filtros (responsive). */
  window.addEventListener("resize", function () {
    clearTimeout(window._jfzResizeT);
    window._jfzResizeT = setTimeout(function () {
      var cuerpoR = $("#jfz-filtros-cuerpo"), panelR = $("#jfz-buscador");
      if (cuerpoR && panelR && panelR.classList.contains("abierto")) cuerpoR.style.maxHeight = cuerpoR.scrollHeight + "px";
    }, 150);
  });
})();
(function () { var m = document.getElementById("jfz-mapa"); if (m && window.JFZ_CONFIG && /^https:\/\/www\.google\.com\/maps\/embed/.test(window.JFZ_CONFIG.MAPA_URL || "")) m.src = window.JFZ_CONFIG.MAPA_URL; })();
