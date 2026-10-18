/* Mejoras de la galería: mosaico de tamaños variados e indicador de fecha al hacer scroll. No modifica jfz.js. */
(function () {
  var S = window.JFZ_FOTOS || [];
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var box = document.getElementById("jfz-galeria");
  if (!box) return;
  var barra = document.getElementById("jfz-tabs");
  if (barra && S.length < 2) barra.style.display = "none";   // con una sola sección no hacen falta pestañas

  function mosaico() {
    if (box.getAttribute("data-plus") || !box.querySelector(".jfz-card")) return;
    box.setAttribute("data-plus", "1");
    Array.prototype.forEach.call(box.querySelectorAll(".row"), function (row) {
      row.classList.add("jfz-mosaico");
      Array.prototype.forEach.call(row.children, function (c, i) {
        if (i % 9 === 0) c.classList.add("jfz-grande"); else if (i % 9 === 5) c.classList.add("jfz-ancho");
      });
    });
  }
  mosaico();
  if (!box.getAttribute("data-plus")) new MutationObserver(mosaico).observe(box, { childList: true });

  /* ----- indicador de fecha ----- */
  var chip = document.createElement("div"); chip.className = "jfz-fecha-chip"; document.body.appendChild(chip);
  var timer, tick = false;

  function etiqueta(card) {
    var sec = card.closest(".jfz-sec"), btn = card.querySelector(".jfz-add");
    var id = sec && sec.getAttribute("data-id"), f = btn && btn.getAttribute("data-f");
    var s = S.filter(function (x) { return x.id === id; })[0];
    var d = s && s.fechas && s.fechas[f];
    if (d) { var p = d.split("-"); return +p[2] + " de " + MESES[+p[1] - 1] + " de " + p[0]; }
    return s ? s.titulo : "";
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
