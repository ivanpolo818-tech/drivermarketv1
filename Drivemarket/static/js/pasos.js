document.addEventListener("DOMContentLoaded", function () {
  let pasoActual = 1;
  const totalPasos = 4;
  const titulos = [
    "PASO 1 DE 4 : DATOS BÁSICOS",
    "PASO 2 DE 4 : CARACTERÍSTICAS",
    "PASO 3 DE 4 : FOTOGRAFÍAS",
    "PASO 4 DE 4 : CONTACTO",
  ];

  const tituloPaso = document.getElementById("tituloPaso");
  const barra = document.getElementById("barraProgreso");

  // Mostrar paso inicial
  mostrarPaso(pasoActual);

  // --- Función principal para mostrar los pasos ---
  function mostrarPaso(paso) {
    // Ocultar todas las secciones
    document.querySelectorAll(".seccion").forEach((s) => (s.style.display = "none"));
    document.querySelectorAll(".paso").forEach((p) => p.classList.remove("activo"));

    // Mostrar la sección y paso actual
    const seccion = document.getElementById("seccion" + paso);
    const indicador = document.getElementById("paso" + paso);
    if (seccion && indicador) {
      seccion.style.display = "block";
      indicador.classList.add("activo");
    }

    // Actualizar título y barra de progreso
    if (tituloPaso) tituloPaso.textContent = titulos[paso - 1];
    if (barra) barra.style.width = ((paso - 1) / (totalPasos - 1)) * 100 + "%";
  }

  // --- Hacer visible globalmente la función siguientePaso() ---
  window.siguientePaso = function (nuevoPaso) {
    if (nuevoPaso >= 1 && nuevoPaso <= totalPasos) {
      pasoActual = nuevoPaso;
      mostrarPaso(pasoActual);
    }
  };

  // --- Previsualización de imágenes ---
  window.previewSeparada = function (input, idx) {
    const file = input.files[0];
    const img = document.getElementById(`preview${idx}`);
    const btn = document.getElementById(`btnDel${idx}`);

    if (!file) {
      img.src = "/static/img/no-image.jpg";
      btn.style.display = "none";
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      img.src = e.target.result;
      btn.style.display = "inline-block";
    };
    reader.readAsDataURL(file);
  };

  // --- Eliminar imagen ---
  window.eliminarSeparada = function (idx) {
    const input = document.getElementById(`imagen${idx}`);
    const img = document.getElementById(`preview${idx}`);
    const btn = document.getElementById(`btnDel${idx}`);

    input.value = "";
    img.src = "/static/img/no-image.jpg";
    btn.style.display = "none";
  };

  // --- Validar que haya al menos 5 imágenes ---
  window.validarImagenesSeparadas = function () {
    let faltan = false; 
    for (let i = 1; i <= 5; i++) {
      const input = document.getElementById(`imagen${i}`);
      if (!input || input.files.length === 0) {
        faltan = true;
        break;
      }
    }
    const mensaje = document.getElementById("mensajeImagenes");
    if (faltan) {
      mensaje.style.display = "block";
    } else {
      mensaje.style.display = "none";
      siguientePaso(4);
    }
  };
});
  