document.addEventListener('DOMContentLoaded', () => {
  const testimonials = document.querySelectorAll('.testimonial-slide');
  let currentTestimonial = 0;
  const testimonialInterval = 6000; // 6 segundos por testimonio

  const showTestimonial = (index) => {
    testimonials.forEach(test => test.style.display = 'none');
    testimonials[index].style.display = 'block';
  };

  const nextTestimonial = () => {
    currentTestimonial = (currentTestimonial + 1) % testimonials.length;
    showTestimonial(currentTestimonial);
  };

  // Inicializa
  showTestimonial(currentTestimonial);
  setInterval(nextTestimonial, testimonialInterval);
});

