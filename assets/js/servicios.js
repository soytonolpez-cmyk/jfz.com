/* ============================================================
   SERVICIOS QUE SE PUEDEN AGREGAR AL CARRITO
   - precio: número en pesos (5000 = $5.000) o null si es "a convenir".
   - aviso: true = al agregarlo sale la ventana con el AVISO_SESION.
   - icono: nombre de un ícono de https://icons.getbootstrap.com (ej. "bi-camera").
   Para agregar un servicio nuevo, copia uno de los bloques, cámbiale el id (sin espacios) y los textos.
   ============================================================ */
window.JFZ_CONFIG.AVISO_SESION =
  "Para las sesiones de fotos y videos debes ir a un punto establecido. " +
  "El desplazamiento hasta ese punto no se cobra ni se paga: corre por cuenta del cliente.";

window.JFZ_CONFIG.SERVICIOS = [
  { id: "sesion-fotos", nombre: "Fotos", icono: "bi-camera", precio: null, precioTexto: "Desde $5.000 por foto",
    nota: "Pagas solo las fotos que elijas: $10.000 c/u, $8.000 c/u desde 3 fotos y $5.000 c/u desde 4. Mismo precio para una o varias personas por foto.", aviso: true },
  { id: "video-short", nombre: "Video corto (short)", icono: "bi-phone", precio: null, precioTexto: "Regalo con 1 foto",
    nota: "30 segundos o menos para redes.Foto solo después de la sesión de fotos.", aviso: true },
  { id: "cinematic", nombre: "Video cinematic", icono: "bi-camera-video", precio: 5000,
    nota: "Varias tomas. Precio por persona. Solo después de la sesión de fotos.", aviso: true },
  { id: "cinematic-short", nombre: "Cinematic + short", icono: "bi-film", precio: 8000,
    nota: "Precio por persona. Solo después de la sesión de fotos.", aviso: true },
  { id: "marco-40x70", nombre: "Foto enmarcada 40x70", icono: "bi-image", precio: null, precioTexto: "Muy pronto",
    nota: "Precio a convenir por WhatsApp.", aviso: false },
  { id: "marco-50x70", nombre: "Foto enmarcada 50x70", icono: "bi-image", precio: null, precioTexto: "Muy pronto",
    nota: "Precio a convenir por WhatsApp.", aviso: false }
];
