// ============================================
// CENTRO DE NOTIFICACIONES - JAVASCRIPT
// ============================================

$(document).ready(function() {
    // Variables globales
    let paginaActual = 1;
    let cargando = false;
    let hayMasNotificaciones = true;
    let filtroActual = { tipo: 'todos', leida: 'todos' };
    
    // Elementos del DOM
    const toastEl = document.getElementById('liveToast');
    const toast = bootstrap.Toast ? new bootstrap.Toast(toastEl) : null;
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    
    // ============================================
    // FUNCIONES UTILITARIAS
    // ============================================
    
    /**
     * Muestra un toast de notificación
     */
    function mostrarToast(titulo, mensaje, tipo = 'info') {
        if (!toast) return;
        
        $('#toastTitle').text(titulo);
        $('#toastMessage').text(mensaje);
        $('#toastTime').text(new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit', 
            minute: '2-digit'
        }));
        
        // Cambiar color del header
        const header = $(toastEl).find('.toast-header');
        header.removeClass('bg-primary bg-success bg-warning bg-danger text-white text-dark');
        
        switch(tipo) {
            case 'success':
                header.addClass('bg-success text-white');
                break;
            case 'warning':
                header.addClass('bg-warning text-dark');
                break;
            case 'danger':
                header.addClass('bg-danger text-white');
                break;
            default:
                header.addClass('bg-primary text-white');
        }
        
        toast.show();
    }
    
    /**
     * Muestra un modal de confirmación
     */
    function mostrarConfirmacion(titulo, mensaje, callback) {
        $('#modalTitle').text(titulo);
        $('#modalBody').text(mensaje);
        
        $('#modalConfirm').off('click').on('click', function() {
            modal.hide();
            callback();
        });
        
        modal.show();
    }
    
    /**
     * Actualiza el contador de notificaciones no leídas
     */
    function actualizarContador() {
        $.get('/notificaciones/no-leidas')
            .done(function(response) {
                if (response.success) {
                    const total = response.total || 0;
                    $('#totalNotificaciones').text(total);
                    $('#headerBadge').text(total);
                    
                    if (total === 0) {
                        $('#headerBadge').hide();
                    } else {
                        $('#headerBadge').show();
                    }
                    
                    // Actualizar total de hoy si viene en la respuesta
                    if (response.total_hoy !== undefined) {
                        $('#totalHoy').text(response.total_hoy);
                    }
                }
            })
            .fail(function() {
                console.error('Error al actualizar contador');
            });
    }
    
    /**
     * Formatea el tiempo transcurrido
     */
    function formatearTiempo(fechaStr) {
        const fecha = new Date(fechaStr);
        const ahora = new Date();
        const diffMs = ahora - fecha;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Ahora mismo';
        if (diffMins < 60) return `Hace ${diffMins} min`;
        if (diffHours < 24) return `Hace ${diffHours} h`;
        if (diffDays === 1) return 'Ayer';
        if (diffDays < 7) return `Hace ${diffDays} días`;
        
        return fecha.toLocaleDateString('es-ES', { 
            day: '2-digit', 
            month: 'short',
            year: fecha.getFullYear() !== ahora.getFullYear() ? 'numeric' : undefined
        });
    }
    
    /**
     * Obtiene la configuración de icono y color según el tipo
     */
    function obtenerConfiguracionTipo(tipo) {
        const configuraciones = {
            'precio_bajo': {
                icono: 'fa-tag',
                color: 'success',
                nombre: 'Precio bajo',
                colorClase: 'icon-success'
            },
            'mensaje_nuevo': {
                icono: 'fa-envelope',
                color: 'primary',
                nombre: 'Mensaje nuevo',
                colorClase: 'icon-primary'
            },
            'favorito': {
                icono: 'fa-heart',
                color: 'danger',
                nombre: 'Favoritos',
                colorClase: 'icon-danger'
            },
            'vehiculo_vendido': {
                icono: 'fa-car',
                color: 'warning',
                nombre: 'Vehículo vendido',
                colorClase: 'icon-warning'
            },
            'oferta_especial': {
                icono: 'fa-gift',
                color: 'info',
                nombre: 'Oferta especial',
                colorClase: 'icon-info'
            },
            'sistema': {
                icono: 'fa-cog',
                color: 'secondary',
                nombre: 'Sistema',
                colorClase: 'icon-secondary'
            }
        };
        
        return configuraciones[tipo] || {
            icono: 'fa-bell',
            color: 'secondary',
            nombre: tipo.replace('_', ' ').toUpperCase(),
            colorClase: 'icon-secondary'
        };
    }
    
    /**
     * Crea el HTML de una notificación
     */
    function crearElementoNotificacion(notif) {
        const config = obtenerConfiguracionTipo(notif.tipo || 'sistema');
        const esLeida = notif.leida || false;
        const tiempo = formatearTiempo(notif.fecha_creacion);
        
        const botonAccion = esLeida ? `
            <button class="action-btn btn-secondary marcar-no-leida" 
                    title="Marcar como no leída" data-id="${notif.id}">
                <i class="far fa-envelope"></i>
            </button>
        ` : `
            <button class="action-btn btn-primary marcar-leida" 
                    title="Marcar como leída" data-id="${notif.id}">
                <i class="far fa-envelope-open"></i>
            </button>
        `;
        
        const enlaceAccion = notif.url_accion ? `
            <a href="${notif.url_accion}" class="notification-link">
                Ver más <i class="fas fa-chevron-right"></i>
            </a>
        ` : '';
        
        return `
            <div class="notification-item ${!esLeida ? 'unread' : ''}" 
                 data-id="${notif.id}" data-tipo="${notif.tipo}">
                <div class="notification-icon ${config.colorClase}">
                    <i class="fas ${config.icono}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-header">
                        <h6 class="notification-title">${notif.titulo || 'Nueva notificación'}</h6>
                        <div class="notification-actions">
                            ${botonAccion}
                            <button class="action-btn btn-danger eliminar-notificacion" 
                                    title="Eliminar" data-id="${notif.id}">
                                <i class="far fa-trash-alt"></i>
                            </button>
                        </div>
                    </div>
                    <p class="notification-message">${notif.mensaje || ''}</p>
                    <div class="notification-footer">
                        <span class="notification-time">
                            <i class="far fa-clock"></i>
                            ${tiempo}
                        </span>
                        <span class="notification-badge badge-${config.color}">
                            ${config.nombre}
                        </span>
                        ${enlaceAccion}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Anima la eliminación de una notificación
     */
    function animarEliminacion($elemento, callback) {
        $elemento.css({
            'transform': 'translateX(-100%)',
            'opacity': '0'
        });
        
        setTimeout(function() {
            $elemento.slideUp(300, function() {
                $(this).remove();
                if (callback) callback();
            });
        }, 300);
    }
    
    /**
     * Verifica si la lista está vacía y muestra mensaje
     */
    function verificarListaVacia() {
        if ($('#listaNotificaciones .notification-item').length === 0) {
            $('#listaNotificaciones').html(`
                <div class="empty-state">
                    <i class="far fa-bell-slash"></i>
                    <h4>No hay notificaciones</h4>
                    <p>Aquí aparecerán tus notificaciones cuando tengas nuevas actividades.</p>
                    <button class="btn btn-primary mt-3" id="recargarNotificacionesBtn">
                        <i class="fas fa-sync-alt me-2"></i>Recargar
                    </button>
                </div>
            `);
        }
    }
    
    // ============================================
    // EVENTOS DE NOTIFICACIONES
    // ============================================
    
    /**
     * Marcar notificación como leída
     */
    $(document).on('click', '.marcar-leida', function(e) {
        e.preventDefault();
        const notificacionId = $(this).data('id');
        const $item = $(this).closest('.notification-item');
        const $boton = $(this);
        
        // Deshabilitar botón mientras se procesa
        $boton.prop('disabled', true);
        
        $.ajax({
            url: `/notificaciones/marcar-leida/${notificacionId}`,
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    // Animar cambio
                    $item.removeClass('unread');
                    
                    // Reemplazar botón
                    const $nuevoBoton = $(`
                        <button class="action-btn btn-secondary marcar-no-leida" 
                                title="Marcar como no leída" data-id="${notificacionId}">
                            <i class="far fa-envelope"></i>
                        </button>
                    `);
                    
                    $boton.fadeOut(200, function() {
                        $(this).replaceWith($nuevoBoton);
                        $nuevoBoton.hide().fadeIn(200);
                    });
                    
                    actualizarContador();
                    mostrarToast('¡Listo!', 'Notificación marcada como leída', 'success');
                }
            },
            error: function(xhr) {
                const mensaje = xhr.responseJSON?.mensaje || 'No se pudo marcar como leída';
                mostrarToast('Error', mensaje, 'danger');
                $boton.prop('disabled', false);
            }
        });
    });
    
    /**
     * Marcar notificación como no leída
     */
    $(document).on('click', '.marcar-no-leida', function(e) {
        e.preventDefault();
        const notificacionId = $(this).data('id');
        const $item = $(this).closest('.notification-item');
        const $boton = $(this);
        
        $boton.prop('disabled', true);
        
        $.ajax({
            url: `/notificaciones/marcar-no-leida/${notificacionId}`,
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    $item.addClass('unread');
                    
                    const $nuevoBoton = $(`
                        <button class="action-btn btn-primary marcar-leida" 
                                title="Marcar como leída" data-id="${notificacionId}">
                            <i class="far fa-envelope-open"></i>
                        </button>
                    `);
                    
                    $boton.fadeOut(200, function() {
                        $(this).replaceWith($nuevoBoton);
                        $nuevoBoton.hide().fadeIn(200);
                    });
                    
                    actualizarContador();
                    mostrarToast('¡Listo!', 'Notificación marcada como no leída', 'success');
                }
            },
            error: function(xhr) {
                const mensaje = xhr.responseJSON?.mensaje || 'No se pudo marcar como no leída';
                mostrarToast('Error', mensaje, 'danger');
                $boton.prop('disabled', false);
            }
        });
    });
    
    /**
     * Eliminar notificación
     */
    $(document).on('click', '.eliminar-notificacion', function(e) {
        e.preventDefault();
        const notificacionId = $(this).data('id');
        const $item = $(this).closest('.notification-item');
        
        mostrarConfirmacion(
            'Eliminar notificación',
            '¿Estás seguro de que quieres eliminar esta notificación? Esta acción no se puede deshacer.',
            function() {
                $.ajax({
                    url: `/notificaciones/eliminar/${notificacionId}`,
                    method: 'DELETE',
                    success: function(response) {
                        if (response.success) {
                            animarEliminacion($item, function() {
                                actualizarContador();
                                verificarListaVacia();
                            });
                            
                            mostrarToast('Eliminada', 'Notificación eliminada correctamente', 'success');
                        }
                    },
                    error: function(xhr) {
                        const mensaje = xhr.responseJSON?.mensaje || 'No se pudo eliminar la notificación';
                        mostrarToast('Error', mensaje, 'danger');
                    }
                });
            }
        );
    });
    
    // ============================================
    // CONTROLES PRINCIPALES
    // ============================================
    
    /**
     * Marcar todas como leídas
     */
    $('#marcarTodasLeidas').click(function() {
        const cantidadNoLeidas = $('.notification-item.unread').length;
        
        if (cantidadNoLeidas === 0) {
            mostrarToast('Información', 'No hay notificaciones sin leer', 'info');
            return;
        }
        
        mostrarConfirmacion(
            'Marcar todas como leídas',
            `¿Estás seguro de que quieres marcar ${cantidadNoLeidas} notificación(es) como leídas?`,
            function() {
                const $boton = $('#marcarTodasLeidas');
                const textoOriginal = $boton.html();
                
                // Mostrar loading
                $boton.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-2"></i>Procesando...');
                
                $.ajax({
                    url: '/notificaciones/marcar-todas-leidas',
                    method: 'POST',
                    success: function(response) {
                        if (response.success) {
                            // Animar cambio en todas las notificaciones
                            $('.notification-item.unread').each(function(index) {
                                const $item = $(this);
                                const notifId = $item.data('id');
                                
                                setTimeout(function() {
                                    $item.removeClass('unread');
                                    
                                    const $botonLeida = $item.find('.marcar-leida');
                                    if ($botonLeida.length) {
                                        $botonLeida.replaceWith(`
                                            <button class="action-btn btn-secondary marcar-no-leida" 
                                                    title="Marcar como no leída" data-id="${notifId}">
                                                <i class="far fa-envelope"></i>
                                            </button>
                                        `);
                                    }
                                }, index * 50);
                            });
                            
                            actualizarContador();
                            mostrarToast('¡Perfecto!', `${response.actualizadas} notificaciones marcadas como leídas`, 'success');
                        }
                    },
                    error: function(xhr) {
                        const mensaje = xhr.responseJSON?.mensaje || 'No se pudieron marcar todas como leídas';
                        mostrarToast('Error', mensaje, 'danger');
                    },
                    complete: function() {
                        $boton.prop('disabled', false).html(textoOriginal);
                    }
                });
            }
        );
    });
    
    /**
     * Recargar notificaciones
     */
    $('#recargarNotificaciones').click(function() {
        const $boton = $(this);
        const $icono = $boton.find('i');
        
        $icono.addClass('fa-spin');
        $boton.prop('disabled', true);
        
        setTimeout(function() {
            location.reload();
        }, 500);
    });
    
    $(document).on('click', '#recargarNotificacionesBtn', function() {
        location.reload();
    });
    
    /**
     * Filtrar notificaciones
     */
    $('.dropdown-item').click(function(e) {
        e.preventDefault();
        
        $('.dropdown-item').removeClass('active');
        $(this).addClass('active');
        
        filtroActual = {
            tipo: $(this).data('tipo'),
            leida: $(this).data('leida')
        };
        
        // Actualizar texto del filtro
        let textoFiltro = 'Mostrando todas';
        
        if (filtroActual.leida === 'no_leidas') {
            textoFiltro = 'Mostrando solo no leídas';
        } else if (filtroActual.leida === 'leidas') {
            textoFiltro = 'Mostrando solo leídas';
        } else if (filtroActual.tipo !== 'todos') {
            textoFiltro = `Mostrando: ${$(this).find('span').text().trim()}`;
        }
        
        $('#contadorFiltro').text(textoFiltro);
        
        // Aplicar filtro
        aplicarFiltro();
    });
    
    /**
     * Aplica los filtros seleccionados
     */
    function aplicarFiltro() {
        const $lista = $('#listaNotificaciones');
        $lista.addClass('pulse-animation');
        
        $.ajax({
            url: '/notificaciones/filtrar',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(filtroActual),
            success: function(response) {
                if (response.success) {
                    if (response.notificaciones.length > 0) {
                        let html = '';
                        response.notificaciones.forEach(notif => {
                            html += crearElementoNotificacion(notif);
                        });
                        
                        $lista.fadeOut(200, function() {
                            $(this).html(html).fadeIn(300);
                        });
                        
                        $('#noMasNotificaciones').hide();
                    } else {
                        $lista.fadeOut(200, function() {
                            $(this).html(`
                                <div class="empty-state">
                                    <i class="far fa-filter"></i>
                                    <h4>No hay notificaciones</h4>
                                    <p>No se encontraron notificaciones con los filtros aplicados.</p>
                                    <button class="btn btn-outline-primary mt-3" id="limpiarFiltros">
                                        <i class="fas fa-times me-2"></i>Limpiar filtros
                                    </button>
                                </div>
                            `).fadeIn(300);
                        });
                    }
                }
            },
            error: function() {
                mostrarToast('Error', 'No se pudieron aplicar los filtros', 'danger');
            },
            complete: function() {
                $lista.removeClass('pulse-animation');
            }
        });
    }
    
    // Limpiar filtros
    $(document).on('click', '#limpiarFiltros', function() {
        $('.dropdown-item[data-tipo="todos"][data-leida="todos"]').click();
    });
    
    // ============================================
    // INFINITE SCROLL
    // ============================================
    
    /**
     * Carga más notificaciones
     */
    function cargarMasNotificaciones() {
        if (cargando || !hayMasNotificaciones) return;
        if (filtroActual.tipo !== 'todos' || filtroActual.leida !== 'todos') return;
        
        cargando = true;
        paginaActual++;
        $('#cargandoNotificaciones').fadeIn(300);
        
        $.ajax({
            url: `/notificaciones/pagina/${paginaActual}`,
            method: 'GET',
            success: function(response) {
                if (response.success && response.notificaciones.length > 0) {
                    let html = '';
                    response.notificaciones.forEach(notif => {
                        html += crearElementoNotificacion(notif);
                    });
                    
                    $('#listaNotificaciones').append(html);
                    hayMasNotificaciones = response.hay_mas;
                    
                    if (!hayMasNotificaciones) {
                        $('#noMasNotificaciones').fadeIn(300);
                    }
                } else {
                    hayMasNotificaciones = false;
                    $('#noMasNotificaciones').fadeIn(300);
                }
            },
            error: function() {
                paginaActual--;
            },
            complete: function() {
                cargando = false;
                $('#cargandoNotificaciones').fadeOut(300);
            }
        });
    }
    
    /**
     * Detectar scroll para infinite scroll
     */
    $(window).scroll(function() {
        if ($(window).scrollTop() + $(window).height() >= $(document).height() - 200) {
            cargarMasNotificaciones();
        }
    });
    
    // ============================================
    // MENU MÓVIL
    // ============================================
    
    $('#mobileMenuToggle').click(function() {
        $('.main-nav').slideToggle(300);
        $(this).find('i').toggleClass('fa-bars fa-times');
    });
    
    // ============================================
    // ANIMACIONES
    // ============================================
    
    // Animación de pulso para contador
    function animarContador() {
        $('#totalNotificaciones, #headerBadge').addClass('pulse-animation');
        setTimeout(function() {
            $('#totalNotificaciones, #headerBadge').removeClass('pulse-animation');
        }, 2000);
    }
    
    // ============================================
    // INICIALIZACIÓN
    // ============================================
    
    // Cargar contador inicial
    actualizarContador();
    
    // Verificar infinite scroll
    hayMasNotificaciones = $('#listaNotificaciones .notification-item').length >= 20;
    
    // Actualizar contador periódicamente
    setInterval(actualizarContador, 30000);
    
    // Animación inicial
    $('.notification-item').each(function(index) {
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
        }, index * 50);
    });
    
    console.log('✅ Sistema de notificaciones cargado correctamente');
});