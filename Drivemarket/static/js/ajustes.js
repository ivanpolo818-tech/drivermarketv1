// ============================================
// AJUSTES - JAVASCRIPT
// ============================================

$(document).ready(function() {
    // ============================================
    // NAVEGACIÓN ENTRE SECCIONES
    // ============================================
    
    $('.sidebar-nav .nav-item').on('click', function(e) {
        e.preventDefault();
        
        // Obtener la sección objetivo
        const targetSection = $(this).data('section');
        
        // Actualizar navegación activa
        $('.sidebar-nav .nav-item').removeClass('active');
        $(this).addClass('active');
        
        // Mostrar sección correspondiente
        $('.settings-section').removeClass('active');
        $(`#${targetSection}`).addClass('active');
        
        // Scroll suave al inicio del contenido
        $('html, body').animate({
            scrollTop: $('.settings-content').offset().top - 100
        }, 300);
        
        // Actualizar URL sin recargar
        if (history.pushState) {
            history.pushState(null, null, `#${targetSection}`);
        }
    });
    
    // Detectar hash en URL al cargar
    if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        $(`.sidebar-nav .nav-item[data-section="${hash}"]`).click();
    }
    
    // ============================================
    // TOGGLE PASSWORD VISIBILITY
    // ============================================
    
    $('.toggle-password').on('click', function() {
        const $input = $(this).siblings('input');
        const $icon = $(this).find('i');
        
        if ($input.attr('type') === 'password') {
            $input.attr('type', 'text');
            $icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            $input.attr('type', 'password');
            $icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
    
    // ============================================
    // PASSWORD STRENGTH INDICATOR
    // ============================================
    
    $('#password-nueva').on('input', function() {
        const password = $(this).val();
        const strength = calculatePasswordStrength(password);
        
        updatePasswordStrength(strength);
    });
    
    function calculatePasswordStrength(password) {
        let strength = 0;
        
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        
        return strength;
    }
    
    function updatePasswordStrength(strength) {
        const $fill = $('.strength-fill');
        const $text = $('.strength-text');
        
        let width, color, text;
        
        if (strength <= 2) {
            width = '33%';
            color = '#ef4444';
            text = 'Débil';
        } else if (strength <= 4) {
            width = '66%';
            color = '#f59e0b';
            text = 'Media';
        } else {
            width = '100%';
            color = '#10b981';
            text = 'Fuerte';
        }
        
        $fill.css({
            'width': width,
            'background-color': color
        });
        
        $text.text(text).css('color', color);
    }
    
    // ============================================
    // VALIDACIÓN DE FORMULARIOS
    // ============================================
    
    // Validar cambio de contraseña
    $('form').on('submit', function(e) {
        e.preventDefault();
        
        const $form = $(this);
        const formId = $form.closest('.settings-section').attr('id');
        
        if (formId === 'seguridad') {
            const passwordActual = $('#password-actual').val();
            const passwordNueva = $('#password-nueva').val();
            const passwordConfirmar = $('#password-confirmar').val();
            
            if (!passwordActual || !passwordNueva || !passwordConfirmar) {
                mostrarToast('Error', 'Por favor completa todos los campos', 'error');
                return;
            }
            
            if (passwordNueva !== passwordConfirmar) {
                mostrarToast('Error', 'Las contraseñas no coinciden', 'error');
                return;
            }
            
            if (passwordNueva.length < 8) {
                mostrarToast('Error', 'La contraseña debe tener al menos 8 caracteres', 'error');
                return;
            }
        }
        
        // Simular guardado
        guardarCambios($form);
    });
    
    function guardarCambios($form) {
        const $submitBtn = $form.find('button[type="submit"]');
        const originalText = $submitBtn.html();
        
        // Mostrar loading
        $submitBtn.prop('disabled', true)
                  .html('<i class="fas fa-spinner fa-spin"></i> Guardando...');
        
        // Simular llamada al servidor
        setTimeout(function() {
            $submitBtn.prop('disabled', false).html(originalText);
            mostrarToast('¡Éxito!', 'Los cambios se guardaron correctamente', 'success');
        }, 1500);
    }
    
    // ============================================
    // CANCELAR CAMBIOS
    // ============================================
    
    $('.btn-secondary').on('click', function() {
        const $form = $(this).closest('form');
        $form[0].reset();
        mostrarToast('Cancelado', 'Los cambios no se guardaron', 'info');
    });
    
    // ============================================
    // CERRAR SESIONES
    // ============================================
    
    $('.session-item .btn-danger-outline').on('click', function() {
        const $session = $(this).closest('.session-item');
        
        // Mostrar modal de confirmación
        $('#confirmModal .modal-title').text('Cerrar Sesión');
        $('#confirmModal .modal-body p').text('¿Estás seguro de que deseas cerrar esta sesión?');
        
        $('#confirmModal .btn-primary').off('click').on('click', function() {
            $session.fadeOut(300, function() {
                $(this).remove();
            });
            
            $('#confirmModal').modal('hide');
            mostrarToast('Sesión cerrada', 'La sesión ha sido cerrada correctamente', 'success');
        });
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    });
    
    // ============================================
    // ACCIONES DE CUENTA
    // ============================================
    
    // Desactivar cuenta
    $('.btn-warning').on('click', function() {
        $('#confirmModal .modal-title').text('Desactivar Cuenta');
        $('#confirmModal .modal-body p').text('¿Estás seguro de que deseas desactivar tu cuenta temporalmente? Podrás reactivarla en cualquier momento.');
        
        $('#confirmModal .btn-primary').off('click').on('click', function() {
            $('#confirmModal').modal('hide');
            mostrarToast('Cuenta desactivada', 'Tu cuenta ha sido desactivada temporalmente', 'warning');
        });
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    });
    
    // Eliminar cuenta
    $('.btn-danger').on('click', function() {
        $('#confirmModal .modal-title').text('⚠️ Eliminar Cuenta Permanentemente');
        $('#confirmModal .modal-body p').text('Esta acción es IRREVERSIBLE. Se eliminarán todos tus datos, publicaciones, mensajes y no podrás recuperar tu cuenta. ¿Estás completamente seguro?');
        
        $('#confirmModal .btn-primary')
            .removeClass('btn-primary')
            .addClass('btn-danger')
            .text('Eliminar Definitivamente')
            .off('click')
            .on('click', function() {
                $('#confirmModal').modal('hide');
                mostrarToast('Cuenta eliminada', 'Tu cuenta ha sido eliminada permanentemente', 'error');
                
                // Redirigir después de 2 segundos
                setTimeout(function() {
                    window.location.href = '/';
                }, 2000);
            });
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    });
    
    // ============================================
    // SUBIR FOTO DE PERFIL
    // ============================================
    
    $('.photo-actions .btn-primary').on('click', function() {
        // Crear input file temporal
        const $input = $('<input type="file" accept="image/*" style="display:none">');
        
        $input.on('change', function(e) {
            const file = e.target.files[0];
            
            if (file) {
                // Validar tamaño
                if (file.size > 5 * 1024 * 1024) {
                    mostrarToast('Error', 'La imagen no debe superar los 5MB', 'error');
                    return;
                }
                
                // Leer y mostrar preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    $('.photo-placeholder').html(`<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`);
                    mostrarToast('¡Listo!', 'Foto actualizada correctamente', 'success');
                };
                reader.readAsDataURL(file);
            }
        });
        
        $input.click();
    });
    
    // Eliminar foto
    $('.photo-actions .btn-secondary').on('click', function() {
        $('.photo-placeholder').html('<i class="fas fa-user"></i>');
        mostrarToast('Eliminada', 'Foto de perfil eliminada', 'info');
    });
    
    // ============================================
    // DESCARGAR DATOS
    // ============================================
    
    $('.data-action-item:first-child .btn').on('click', function() {
        const $btn = $(this);
        const originalText = $btn.text();
        
        $btn.prop('disabled', true)
            .html('<i class="fas fa-spinner fa-spin me-2"></i>Preparando...');
        
        setTimeout(function() {
            $btn.prop('disabled', false).text(originalText);
            mostrarToast('Descarga lista', 'Tu archivo está listo para descargar', 'success');
            
            // Simular descarga
            const link = document.createElement('a');
            link.href = '#';
            link.download = 'mis_datos_drivemarket.zip';
            link.click();
        }, 2000);
    });
    
    // Ver historial
    $('.data-action-item:last-child .btn').on('click', function() {
        mostrarToast('Próximamente', 'Esta función estará disponible pronto', 'info');
    });
    
    // ============================================
    // TOAST NOTIFICATIONS
    // ============================================
    
    function mostrarToast(titulo, mensaje, tipo = 'info') {
        const $toast = $('#liveToast');
        const $header = $toast.find('.toast-header');
        const $title = $toast.find('.toast-header strong');
        const $body = $toast.find('.toast-body');
        
        // Configurar icono y colores según tipo
        let icon = 'fa-check-circle';
        let bgClass = 'bg-success';
        
        switch(tipo) {
            case 'success':
                icon = 'fa-check-circle';
                bgClass = 'bg-success';
                break;
            case 'error':
                icon = 'fa-exclamation-circle';
                bgClass = 'bg-danger';
                break;
            case 'warning':
                icon = 'fa-exclamation-triangle';
                bgClass = 'bg-warning';
                break;
            case 'info':
                icon = 'fa-info-circle';
                bgClass = 'bg-info';
                break;
        }
        
        // Actualizar contenido
        $header.removeClass('bg-success bg-danger bg-warning bg-info text-white text-dark')
               .addClass(`${bgClass} text-white`);
        $toast.find('i:first').attr('class', `fas ${icon} me-2`);
        $title.text(titulo);
        $body.text(mensaje);
        
        // Mostrar toast
        const toast = new bootstrap.Toast($toast[0]);
        toast.show();
    }
    
    // ============================================
    // ANIMACIONES Y EFECTOS
    // ============================================
    
    // Efecto de hover en cards
    $('.settings-card').hover(
        function() {
            $(this).css('transform', 'translateY(-2px)');
        },
        function() {
            $(this).css('transform', 'translateY(0)');
        }
    );
    
    // Animación de entrada
    $('.settings-card').each(function(index) {
        $(this).css({
            'opacity': '0',
            'transform': 'translateY(20px)'
        });
        
        setTimeout(() => {
            $(this).css({
                'opacity': '1',
                'transform': 'translateY(0)',
                'transition': 'all 0.3s ease'
            });
        }, index * 100);
    });
    
    // ============================================
    // INICIALIZACIÓN
    // ============================================
    
    console.log('✅ Página de ajustes cargada correctamente');
});