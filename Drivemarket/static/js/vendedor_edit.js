document.addEventListener("DOMContentLoaded", () => {
    // Toggle negociable slider
    const toggleNeg = document.getElementById('toggleNeg');
    if (toggleNeg) {
        toggleNeg.addEventListener('change', function(){
            const slider = document.getElementById('sliderNeg');
            const thumb = slider.querySelector('span');
            slider.style.background = this.checked ? 'var(--pr)' : 'var(--bd)';
            thumb.style.transform = this.checked ? 'translateX(18px)' : 'translateX(0)';
        });
    }
});

function cambiarEstadoEdit(vid, estado){
    // Configuración de Toast Premium
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer)
            toast.addEventListener('mouseleave', Swal.resumeTimer)
        }
    });

    fetch(`/vendedor/vehiculo/${vid}/estado`, {
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:`estado=${estado}`
    })
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            const labels = {
                activo: 'Vehículo activado correctamente',
                pausado: 'Vehículo pausado',
                vendido: 'Marcado como vendido'
            };
            Toast.fire({
                icon: 'success',
                title: labels[estado] || 'Estado actualizado',
                background: '#fff',
                color: '#000',
                iconColor: '#FF6A00'
            });
            // Recargar después de un momento para ver cambios si es necesario
            setTimeout(() => window.location.reload(), 2000);
        } else {
            Swal.fire({
                title: 'Error',
                text: data.msg || 'No se pudo actualizar el estado',
                icon: 'error',
                confirmButtonColor: '#FF6A00'
            });
        }
    })
    .catch(() => {
        Swal.fire({
            title: 'Error de conexión',
            text: 'No se pudo conectar con el servidor',
            icon: 'warning',
            confirmButtonColor: '#FF6A00'
        });
    });
}
