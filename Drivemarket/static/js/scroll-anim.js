const animatedElements = document.querySelectorAll('.step, .opcion, .info-publicidad, .partners, .cards');

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if(entry.isIntersecting) {
      entry.target.classList.add('fade-in');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

animatedElements.forEach(el => observer.observe(el));
