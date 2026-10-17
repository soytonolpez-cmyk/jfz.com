/* JuanetoFZ — encabezado, pie, galería por trimestres, carrito, login con Google y envío por WhatsApp */
(function () {
  "use strict";
  var C = window.JFZ_CONFIG, S = window.JFZ_FOTOS || [];
  var RUTA = "fotos/";
  var MAPA = {};   // nombre de archivo -> ruta completa (carpeta del trimestre)
  S.forEach(function (s) { s.fotos.forEach(function (f) { if (!MAPA[f]) MAPA[f] = RUTA + s.carpeta + "/" + f; }); });
  var user = null, cart = [], pending = null, auth = null, fb = null, lightbox = null;
  var demo = location.protocol === "file:" || !C.FIREBASE || !C.FIREBASE.apiKey || /PEGA/.test(C.FIREBASE.apiKey);

  /* ---------- utilidades ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function money(n) { return "$" + Number(n).toLocaleString("es-CO"); }
  function base(f) { return f.replace(/\.jpg$/i, ""); }
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
    var sub = S.map(function (s) { return '<li><a href="gallery.html#' + s.id + '">' + esc(s.titulo) + "</a></li>"; }).join("");
    var h = $("#header");
    if (h) h.innerHTML =
      '<div class="container-fluid position-relative d-flex align-items-center justify-content-between">' +
      '<a href="index.html" class="logo d-flex align-items-center me-auto me-xl-0"><img src="assets/img/logo.png" alt="Logo JFZ"><h1 class="sitename">JuanetoFZ</h1></a>' +
      '<nav id="navmenu" class="navmenu"><ul>' +
      '<li><a href="index.html"' + act("inicio") + ">Inicio</a></li>" +
      '<li><a href="about.html"' + act("sobre-mi") + ">Sobre mí</a></li>" +
      '<li class="dropdown"><a href="gallery.html"' + act("galeria") + '><span>Galería</span> <i class="bi bi-chevron-down toggle-dropdown"></i></a><ul>' + sub + "</ul></li>" +
      '<li><a href="services.html"' + act("servicios") + ">Servicios</a></li>" +
      '<li><a href="contact.html"' + act("contacto") + ">Contacto</a></li>" +
      '</ul><i class="mobile-nav-toggle d-xl-none bi bi-list"></i></nav>' +
      '<div class="jfz-actions">' +
      '<a class="jfz-cart-link" href="carrito.html" aria-label="Carrito de compras"><i class="bi bi-cart3"></i><span class="jfz-badge" id="jfz-badge">0</span></a>' +
      '<button type="button" id="jfz-auth" class="jfz-auth"></button></div></div>';
    var f = $("#footer");
    if (f) {
      var soc = [["INSTAGRAM", "bi-instagram"], ["TIKTOK", "bi-tiktok"], ["FACEBOOK", "bi-facebook"], ["YOUTUBE", "bi-youtube"]]
        .filter(function (x) { return C[x[0]]; })
        .map(function (x) { return '<a href="' + C[x[0]] + '" target="_blank" rel="noopener" aria-label="' + x[0] + '"><i class="bi ' + x[1] + '"></i></a>'; }).join("");
      f.innerHTML = '<div class="container"><div class="copyright text-center"><p>© <span>Copyright</span> <strong class="px-1 sitename">JuanetoFZ</strong> <span>Todos los derechos reservados</span></p></div>' +
        '<div class="social-links d-flex justify-content-center">' + soc + "</div>" +
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
      btn.innerHTML = on ? '<i class="bi bi-check-lg"></i> En el carrito' : '<i class="bi bi-cart-plus"></i> Agregar';
      var fig = btn.closest(".jfz-card"); if (fig) fig.classList.toggle("is-selected", on);
    });
    $$(".jfz-svc-add").forEach(function (btn) {
      var on = has("svc:" + btn.getAttribute("data-s"));
      btn.classList.toggle("on", on);
      btn.innerHTML = on ? '<i class="bi bi-check-lg"></i> En el carrito' : '<i class="bi bi-cart-plus"></i> Agregar al carrito';
    });
    renderCartPage();
  }

  /* ---------- galería ---------- */
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
  function renderGallery() {
    var box = $("#jfz-galeria"); if (!box) return;
    var tabs = $("#jfz-tabs");
    tabs.innerHTML = '<button type="button" data-id="todos">Todos</button>' + S.map(function (s) { return '<button type="button" data-id="' + s.id + '">' + esc(s.titulo) + "</button>"; }).join("");
    box.innerHTML = S.map(function (s) {
      return '<section class="jfz-sec" data-id="' + s.id + '" id="sec-' + s.id + '"><h2 class="jfz-sec-title">' + esc(s.titulo) + ' <small>' + s.fotos.length + " fotos</small></h2>" +
        '<div class="row gy-4">' + (s.fotos.length ? s.fotos.map(function (f) { return cardHTML(f, s.id, s.carpeta); }).join("") : '<p class="jfz-empty">Próximamente.</p>') + "</div></section>";
    }).join("");
    wireAdd(box);
    tabs.addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) location.hash = b.getAttribute("data-id"); });
    window.addEventListener("hashchange", showTab);
    showTab(); syncCart();
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
    var u = S.length ? S[S.length - 1] : null;
    var all = u ? u.fotos.slice(0, 8) : [];
    box.innerHTML = all.map(function (f) { return cardHTML(f, "inicio", u.carpeta); }).join("");
    wireAdd(box); initLightbox(); syncCart();
  }

  /* ---------- página del carrito ---------- */
  function compact(files) {
    var nums = files.map(function (f) { var m = f.match(/^IMG_(\d+)\.jpg$/i); return m ? +m[1] : null; });
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
  function buildMessage(compactMode) {
    var t = totals(), ph = photos(), sv = svcs();
    var L = ["Hola Juaneto 👋 Quiero hacer este pedido:", "", "Nombre: " + (user.name || "-"), "Correo: " + (user.email || "-"), ""];
    if (ph.length) {
      L.push("FOTOS (" + ph.length + "):");
      if (compactMode) L.push(compact(ph)); else ph.forEach(function (f, i) { L.push((i + 1) + ". " + f); });
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
    return L.join("\n");
  }
  function sendWhatsApp() {
    if (!cart.length) return;
    if (/X/i.test(C.WHATSAPP)) { alert("Falta configurar el número de WhatsApp en assets/js/config.js"); return; }
    var url = "https://wa.me/" + C.WHATSAPP + "?text=" + encodeURIComponent(buildMessage(false));
    if (url.length > 1900) url = "https://wa.me/" + C.WHATSAPP + "?text=" + encodeURIComponent(buildMessage(true));
    window.open(url, "_blank", "noopener");
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
})();
(function () { var m = document.getElementById("jfz-mapa"); if (m && window.JFZ_CONFIG && /^https:\/\/www\.google\.com\/maps\/embed/.test(window.JFZ_CONFIG.MAPA_URL || "")) m.src = window.JFZ_CONFIG.MAPA_URL; })();
