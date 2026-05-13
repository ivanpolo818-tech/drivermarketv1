/* ═══════════════════════════════════════════════════
   NOTIFICACIONES CENTRO - LÓGICA
   Notification Management for DriveMarket
   ═══════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
    
    /* ── SISTEMA DE TOASTS ── */
    function showToast(title, msg, isSuccess = true) {
        const wrap = document.getElementById('toastWrap');
        if (!wrap) return;
        
        const t = document.createElement('div');
        t.className = 'toast-item';
        const icon = isSuccess 
            ? '<i class="fas fa-check-circle" style="color: #10b981"></i>' 
            : '<i class="fas fa-info-circle" style="color: #3b82f6"></i>';
            
        t.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-body">
                <div class="toast-title">${title}</div>
                <div class="toast-msg">${msg}</div>
            </div>
        `;
        
        wrap.appendChild(t);
        
        // Auto-remove
        setTimeout(() => {
            t.style.animation = 'toastIn 0.4s reverse forwards';
            setTimeout(() => t.remove(), 400);
        }, 4000);
    }

    /* ── SISTEMA DE MODAL ── */
    function openModal(title, body, confirmText, callback) {
        const ov = document.getElementById('confirmModal');
        if (!ov) return;
        
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').textContent = body;
        document.getElementById('modalConfirm').textContent = confirmText;
        
        ov.classList.add('open');
        
        const close = () => ov.classList.remove('open');
        
        document.getElementById('modalConfirm').onclick = () => {
            close();
            callback();
        };
        
        document.getElementById('modalCancel').onclick = close;
        ov.onclick = (e) => { if(e.target === ov) close(); };
    }

    /* ── ACTUALIZAR CONTADORES ── */
    function updateCounters() {
        const unreadCount = document.querySelectorAll('.notif-item.unread').length;
        const sidebarCount = document.getElementById('totalNoLeidas');
        const headerBadge = document.getElementById('badgeNotificaciones');
        
        if (sidebarCount) sidebarCount.textContent = unreadCount;
        if (headerBadge) {
            headerBadge.textContent = unreadCount;
            if (unreadCount > 0) headerBadge.classList.remove('d-none');
            else headerBadge.classList.add('d-none');
        }
    }

    /* ── DELEGACIÓN DE EVENTOS PARA ITEMS ── */
    document.getElementById('notifList')?.addEventListener('click', function(e) {
        const btnRead = e.target.closest('.rbtn');
        const btnUnread = e.target.closest('.ubtn');
        const btnDelete = e.target.closest('.dbtn');

        // Marcar como leída
        if (btnRead) {
            const item = btnRead.closest('.notif-item');
            const id = item.dataset.id;
            
            fetch(`/notificaciones/marcar-leida/${id}`, { method: 'POST', cache: 'no-store' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        item.classList.remove('unread');
                        item.dataset.leida = 'true';
                        btnRead.classList.replace('rbtn', 'ubtn');
                        btnRead.title = 'Marcar no leída';
                        btnRead.innerHTML = '<i class="fas fa-envelope"></i>';
                        updateCounters();
                        showToast('Notificación leída', 'Se ha actualizado el estado.');
                    }
                });
        }

        // Marcar como no leída
        if (btnUnread) {
            const item = btnUnread.closest('.notif-item');
            const id = item.dataset.id;
            
            fetch(`/notificaciones/marcar-no-leida/${id}`, { method: 'POST', cache: 'no-store' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        item.classList.add('unread');
                        item.dataset.leida = 'false';
                        btnUnread.classList.replace('ubtn', 'rbtn');
                        btnUnread.title = 'Marcar como leída';
                        btnUnread.innerHTML = '<i class="fas fa-check"></i>';
                        updateCounters();
                        showToast('Marcada como nueva', 'La notificación vuelve a estar pendiente.', false);
                    }
                });
        }

        // Eliminar individual
        if (btnDelete) {
            const item = btnDelete.closest('.notif-item');
            const id = item.dataset.id;
            
            openModal('Eliminar notificación', '¿Quieres borrar esta notificación de tu historial?', 'Eliminar', () => {
                fetch(`/notificaciones/eliminar/${id}`, { method: 'DELETE', cache: 'no-store' })
                    .then(r => r.json())
                    .then(d => {
                        if (d.success) {
                            item.classList.add('removing');
                            setTimeout(() => {
                                item.remove();
                                updateCounters();
                                checkEmptyState();
                            }, 300);
                            showToast('Eliminada', 'La notificación fue borrada permanentemente.');
                        }
                    });
            });
        }
    });

    /* ── VERIFICAR ESTADO VACÍO ── */
    function checkEmptyState() {
        const list = document.getElementById('notifList');
        const items = list.querySelectorAll('.notif-item');
        if (items.length === 0 && !document.getElementById('emptyState')) {
            list.innerHTML = `
                <div class="empty-state" id="emptyState">
                    <div class="empty-icon"><i class="fas fa-check-circle"></i></div>
                    <h3>Bandeja impecable</h3>
                    <p>No tienes notificaciones pendientes. Todo está al día y bajo control.</p>
                    <button class="action-btn primary" onclick="location.reload()"><i class="fas fa-sync-alt"></i> Verificar de nuevo</button>
                </div>`;
        }
    }

    /* ── ACCIONES MASIVAS ── */
    
    // Marcar todas como leídas
    document.getElementById('markAllRead')?.addEventListener('click', () => {
        const unreadItems = document.querySelectorAll('.notif-item.unread');
        if (!unreadItems.length) {
            showToast('Todo al día', 'No hay notificaciones nuevas.', false);
            return;
        }

        fetch('/notificaciones/marcar-todas-leidas', { method: 'POST', cache: 'no-store' })
            .then(r => r.json())
            .then(d => {
                if (d.success) {
                    unreadItems.forEach(item => {
                        item.classList.remove('unread');
                        item.dataset.leida = 'true';
                        const btn = item.querySelector('.rbtn');
                        if (btn) {
                            btn.classList.replace('rbtn', 'ubtn');
                            btn.innerHTML = '<i class="fas fa-envelope"></i>';
                        }
                    });
                    updateCounters();
                    showToast('Bandeja limpia', 'Todas las notificaciones fueron marcadas como leídas.');
                }
            });
    });

    // Eliminar leídas
    document.getElementById('deleteAllBtn')?.addEventListener('click', () => {
        const readItems = document.querySelectorAll('.notif-item:not(.unread)');
        if (!readItems.length) {
            showToast('No hay elementos', 'No tienes notificaciones leídas para borrar.', false);
            return;
        }

        openModal('Limpiar historial', `Se eliminarán ${readItems.length} notificaciones antiguas.`, 'Limpiar', () => {
            // Este es un proceso asíncrono, Ideally would have a bulk delete route
            // For now we simulate it or call the route if it exists. 
            // The route /marcar-todas-leidas exists but not a bulk delete yet?
            // Actually, let's just do it in the DOM as it was before, or if there's no bulk delete route.
            readItems.forEach(item => {
                const id = item.dataset.id;
                fetch(`/notificaciones/eliminar/${id}`, { method: 'DELETE', cache: 'no-store' });
                item.classList.add('removing');
                setTimeout(() => item.remove(), 300);
            });
            setTimeout(checkEmptyState, 350);
            setTimeout(updateCounters, 400);
            showToast('Historial limpio', 'Las notificaciones antiguas fueron eliminadas.');
        });
    });

    /* ── FILTROS LATERALES ── */
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const filter = this.dataset.filter;
            document.querySelectorAll('.notif-item').forEach(item => {
                let show = true;
                if (filter === 'unread' && item.dataset.leida === 'true') show = false;
                if (filter !== 'all' && filter !== 'unread' && item.dataset.tipo !== filter) show = false;
                
                item.style.display = show ? 'flex' : 'none';
            });
        });
    });

    /* ── REFRESCAR SIMULADO ── */
    document.getElementById('reloadBtn')?.addEventListener('click', function() {
        const icon = this.querySelector('i');
        icon.style.transition = 'transform 1s ease';
        icon.style.transform = 'rotate(360deg)';
        
        setTimeout(() => {
            location.reload();
        }, 600);
    });

    // Initialize counters
    updateCounters();
});
