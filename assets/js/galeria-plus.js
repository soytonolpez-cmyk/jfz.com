/* Mejoras de la galería: mosaico de tamaños variados, indicador de fecha al hacer scroll
   y comportamiento "pegajoso" del panel de filtros (se pega bajo el menú al desplazarse y
   vuelve a su lugar al subir). La barra de búsqueda y las etiquetas motos/caras/cascos
   fueron BORRADAS del código a pedido del dueño del sitio. */
(function () {
  var S = window.JFZ_FOTOS || [];
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var box = document.getElementById("jfz-galeria");
  if (!box) return;
  var barra = document.getElementById("jfz-tabs");
  if (barra && S.length < 2) barra.style.display = "none";   // con una sola sección no hacen falta pestañas

  /* ---------- alta real del menú -> --jfz-header-h (para que los filtros se peguen justo debajo) ---------- */
  function medirHeader() {
    var h = document.getElementById("header");
    if (!h) return;
    document.documentElement.style.setProperty("--jfz-header-h", Math.round(h.getBoundingClientRect().height) + "px");
  }
  medirHeader();
  window.addEventListener("resize", medirHeader);
  if (typeof ResizeObserver !== "undefined") { try { new ResizeObserver(medirHeader).observe(document.getElementById("header")); } catch (e) {} }

  /* ---------- panel de filtros pegajoso: aplica/quita el position cuando toca ---------- */
  var panel = document.getElementById("jfz-buscador");
  if (panel && "IntersectionObserver" in window) {
    var centinela = document.createElement("div");
    centinela.className = "jfz-centinela";
    panel.parentNode.insertBefore(centinela, panel);
    function vigilar() {
      var alto = panel.offsetHeight || 0;
      var off = Math.round(alto * 0.35);          // umbral dentro del propio panel
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          panel.classList.toggle("jfz-pegado", !en.isIntersecting);   // true = está pegado a la pantalla
        });
      }, { rootMargin: "-" + off + "px 0px 0px 0px", threshold: 0 });
      obs.observe(centinela);
      panel._obs = obs;
    }
    vigilar();
    window.addEventListener("resize", function () { if (panel._obs) { try { panel._obs.disconnect(); } catch (e) {} } vigilar(); });
  }

  function mosaico() {
    if (!box.querySelector(".jfz-card")) return;
    Array.prototype.forEach.call(box.querySelectorAll(".row"), function (row) {
      row.classList.add("jfz-mosaico");
      var cols = row.children;
      for (var i = 0; i < cols.length; i++) cols[i].classList.remove("jfz-grande", "jfz-ancho");
      Array.prototype.forEach.call(cols, function (c, i) {
        if (i % 9 === 0) c.classList.add("jfz-grande"); else if (i % 9 === 5) c.classList.add("jfz-ancho");
      });
    });
  }
  /* se aplica tras cada pintado de la galería (sin MutationObserver para no pelear con el DOM) */
  window.addEventListener("jfz-gallery-painted", mosaico);
  setTimeout(mosaico, 300);
  setInterval(function () { if (!document.querySelector(".jfz-mosaico")) mosaico(); }, 1200);

  /* ----- indicador de fecha ----- */
  var chip = document.createElement("div"); chip.className = "jfz-fecha-chip"; document.body.appendChild(chip);
  var timer, tick = false;

  function etiqueta(card) {
    var sec = card.closest(".jfz-sec"), btn = card.querySelector(".jfz-add");
    var id = sec && sec.getAttribute("data-id"), f = btn && btn.getAttribute("data-f");
    var s = S.filter(function (x) { return x.id === id; })[0];
    var d = s && s.fechas && s.fechas[f];
    if (d) { var p = d.split("-"); return +p[2] + " de " + MESES[+p[1] - 1] + " de " + p[0]; }
    /* Si la única sección se llama igual que la página («Galería»), el chip muestra
       «Fotos» para no repetir el nombre dos veces en pantalla. */
    if (s) {
      var t = String(s.titulo).trim().toLowerCase();
      return t === "galeria" ? "Fotos" : s.titulo;
    }
    return "";
  }
  function visible() {
    var best = null, bestTop = 1e9;
    Array.prototype.forEach.call(document.querySelectorAll(".jfz-sec:not([hidden]) .jfz-card"), function (c) {
      var r = c.getBoundingClientRect();
      if (r.bottom > 110 && r.top < window.innerHeight && r.top < bestTop) { best = c; bestTop = r.top; }
    });
    return best;
  }
  function mostrar() {
    var c = visible(); if (!c) return;
    chip.textContent = etiqueta(c);
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var frac = max > 0 ? Math.min(1, window.scrollY / max) : 0;
    chip.style.top = (80 + frac * (window.innerHeight - 160)) + "px";
    chip.classList.add("on");
    clearTimeout(timer); timer = setTimeout(function () { chip.classList.remove("on"); }, 1300);
  }
  window.addEventListener("scroll", function () {
    if (tick) return; tick = true;
    requestAnimationFrame(function () { tick = false; mostrar(); });
  }, { passive: true });
  window.addEventListener("mousemove", function (e) { if (e.clientX > window.innerWidth - 70) mostrar(); }, { passive: true });
})();
