/* static/js/vendedor_inventory.js */

(function() {
    "use strict";

    document.addEventListener('DOMContentLoaded', function(){
        const filterContainer = document.getElementById('vehicleFilters');
        const searchInput = document.getElementById('searchVehicles');
        const notifBtn = document.getElementById('notifBtn');
        const notifDropdown = document.getElementById('notifDropdown');

        // Filter tabs
        if(filterContainer) {
            filterContainer.addEventListener('click', function(e){
                const btn = e.target.closest('button');
                if(!btn) return;
                
                document.querySelectorAll('.v-filter').forEach(b => {
                    b.classList.remove('v-filter-on');
                });
                btn.classList.add('v-filter-on');
                
                const f = btn.dataset.filter;
                document.querySelectorAll('.vehicle-card').forEach(c => {
                    c.style.display = (f === 'all' || c.dataset.status === f) ? '' : 'none';
                });
            });
        }

        // Search
        if(searchInput) {
            searchInput.addEventListener('input', function(){
                const q = this.value.toLowerCase();
                document.querySelectorAll('.vehicle-card').forEach(c => {
                    const text = c.textContent.toLowerCase();
                    c.style.display = text.includes(q) ? '' : 'none';
                });
            });
        }

        // Notifications Toggle
        if(notifBtn && notifDropdown) {
            notifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = notifDropdown.style.display === 'none' || !notifDropdown.style.display;
                notifDropdown.style.display = isHidden ? 'block' : 'none';
            });
            document.addEventListener('click', () => {
                if(notifDropdown) notifDropdown.style.display = 'none';
            });
        }

        // Close dropdown menus on outside click
        document.addEventListener('click', function(e){
            if(!e.target.closest('[id^="menu_wrap_"]')) {
                document.querySelectorAll('[id^="ddmenu_"]').forEach(m => m.style.display='none');
            }
        });
    });

    // Global functions (exposed to window for inline onclick handlers)
    window.toggleMenu = function(id){
        const m = document.getElementById('ddmenu_'+id);
        if(!m) return;
        const wasOpen = m.style.display === 'block';
        document.querySelectorAll('[id^="ddmenu_"]').forEach(x => x.style.display = 'none');
        m.style.display = wasOpen ? 'none' : 'block';
        if(event) event.stopPropagation();
    };

    window.cambiarEstado = function(vid, estado){
        fetch(`/vendedor/vehiculo/${vid}/estado`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `estado=${estado}`
        })
        .then(r => r.json())
        .then(data => {
            if(!data.ok){ 
                alert('Error: ' + (data.msg || 'desconocido')); 
                return; 
            }
            const card  = document.getElementById('card_'+vid);
            const badge = document.getElementById('badge_'+vid);
            if(!card || !badge) return;

            card.dataset.status = estado;
            
            // Update badge (matching dashboard visual style)
            const badges = {
                activo:  { text: '● ACTIVO',  bg: '#10B981' },
                pausado: { text: '⏸ PAUSADO', bg: '#6B7280' },
                vendido: { text: '✔ VENDIDO', bg: '#F59E0B' },
                eliminado: { text: '🗑 ELIMINADO', bg: '#EF4444' }
            };
            
            if(estado === 'eliminado') {
                card.style.opacity = '0';
                setTimeout(() => card.remove(), 400);
                return;
            }

            const bInfo = badges[estado] || { text: estado.toUpperCase(), bg: '#6B7280' };
            badge.textContent = bInfo.text;
            badge.style.background = bInfo.bg;
            
            // Dim card if not active
            card.style.opacity = estado === 'activo' ? '1' : '.65';
            
            // Hide menu
            const m = document.getElementById('ddmenu_'+vid);
            if(m) m.style.display = 'none';
        })
        .catch(err => console.error('Error de conexión:', err));
    };

    window.toggleFeatured = function(vid){
        fetch(`/vendedor/vehiculo/${vid}/toggle-destacado`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if(!data.ok){ 
                alert(data.msg || 'Error al destacar'); 
                return; 
            }
            const btn = document.getElementById('star_'+vid);
            if(!btn) return;
            const ico = btn.querySelector('i');
            if(data.destacado){
                btn.style.color = '#F59E0B';
                ico.className = 'fas fa-star';
            } else {
                btn.style.color = '#fff';
                ico.className = 'far fa-star';
            }
        })
        .catch(err => console.error('Error de conexión:', err));
    };

    window.shareWhatsApp = function(id, name, price, slug) {
        // Usar slug si está disponible, si no ID (compatibilidad SEO)
        const identifier = slug || id;
        const url = window.location.origin + '/vehiculo/' + identifier;
        const msg = `🚗 *¡Mira esta oportunidad en Drive Market!* \n\nVendo mi *${name}*\n💰 Precio: *$${price}*\n\n✅ Excelente estado\n✅ Fotos y detalles aquí:\n${url}\n\n_Compartido desde mi Panel de Vendedor Drive Market_`;
        window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
    };

})();
