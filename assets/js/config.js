/* ============================================================
   CONFIGURACIÓN DEL SITIO  —  lo único que debes editar aquí
   ============================================================ */
window.JFZ_CONFIG = {

  // 1) WhatsApp que recibe los pedidos. Solo números, con indicativo de país.
  //    Colombia = 57. Ejemplo: "573001234567"
  WHATSAPP: "573045508474",

  // 2) Datos de contacto que se muestran en la página Contacto
  TELEFONO: "+57 304 550 8474",
  CORREO: "juanetobiker@gmail.com",
  UBICACION: "https://maps.app.goo.gl/R5f2fJRUgF6eZJ6Z9",
  INSTAGRAM: "https://www.instagram.com/juaneto.biker",
  // Otras redes: pega el enlace entre comillas y aparecerán solas. Déjalas "" si no aplican.
  TIKTOK: "",
  FACEBOOK: "",
  YOUTUBE: "",

  // 3) Precio por foto según cuántas fotos elija el cliente (en pesos).
  //    "desde" = cantidad mínima de fotos. Con 2 fotos se cobra el precio de 1 (ajústalo si quieres).
  PRECIOS: [
    { desde: 1, precio: 10000 },
    { desde: 3, precio: 8000 },
    { desde: 4, precio: 5000 }
  ],

  // 4) Firebase (inicio de sesión con Google). Pega aquí los datos de tu app web de Firebase.
  //    Mientras digan "PEGA_AQUI", el sitio funciona en MODO PRUEBA (sin Google real).
  FIREBASE: {
    apiKey: "AIzaSyBId3vkGVg6Xa-Wu2Ui6aGjsbxWeCUs5Ic",
    authDomain: "database-fotomoteros.firebaseapp.com",
    projectId: "database-fotomoteros",
    appId: "1:37802242353:web:8be17d57ee76a34b324010"
  },

  // 5) Mapa de la página Contacto. Debe ser el enlace de "Insertar un mapa" de Google Maps
  //    (empieza por https://www.google.com/maps/embed?pb=...). Los enlaces cortos tipo
  //    maps.app.goo.gl NO funcionan aquí y se ignoran. Mientras tanto se muestra Medellín.
  //    Tu enlace corto (guardado por si lo necesitas): https://maps.app.goo.gl/R5f2fJRUgF6eZJ6Z9
  MAPA_URL: ""
};
