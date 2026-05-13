function cambiarImagen(url, thumb) {
  const main = document.getElementById("mainImage");
  main.style.opacity = 0;
  setTimeout(() => {
    main.src = url;
    main.style.opacity = 1;
  }, 200);

  document.querySelectorAll(".miniaturas img").forEach(i => i.classList.remove("activa"));
  thumb.classList.add("activa");
}
