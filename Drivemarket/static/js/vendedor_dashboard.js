/* static/js/vendedor_dashboard.js */
(function() {
  const root = document.documentElement;
  const darkToggle = document.getElementById('darkToggle');
  const modal = document.getElementById('modalOverlay');
  const modalInputContainer = document.getElementById('modalInputContainer');
  const modalInput = document.getElementById('modalInput');
  const modalBtnConfirm = document.getElementById('modalBtnConfirm');
  const modalBtnCancel = document.getElementById('modalBtnCancel');
  
  let isDark = localStorage.getItem('dashDark') === '1';
  let mainChart = null;
  let inventoryChart = null;
  let activeVid = null;
  let activeValue = null;

  function applyDark(d) { 
    if (d) {
      root.setAttribute('data-dark','');
    } else {
      root.removeAttribute('data-dark');
    }
    isDark = d; 
    localStorage.setItem('dashDark', d ? '1' : '0'); 
  }
  
  // Inicialización inmediata del tema
  applyDark(isDark);
  
  if (darkToggle) {
    darkToggle.addEventListener('click', () => applyDark(!isDark));
  }

  // ── KPI ANIMATION ──
  function animateCount(el) {
    const target = parseInt(el.dataset.count) || 0;
    const fmt = el.dataset.format || 'number';
    const prefix = el.dataset.prefix || '';
    const duration = 1400;
    const startTime = performance.now();

    function format(val) {
      if (fmt === 'currency') return prefix + val.toLocaleString('en-US');
      if (fmt === 'compact') return val >= 1000 ? (val/1000).toFixed(0) + 'K' : val.toString();
      return prefix + Math.round(val).toLocaleString('en-US');
    }

    function step(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 4);
      el.textContent = format(Math.round(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ── CHARTING LOGIC (Chart.js) ──
  function sparkline(id, data, color) {
    if (typeof Chart === 'undefined') return console.warn("Chart.js no cargado aún para", id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    try {
      const g = ctx.getContext('2d');
      const grad = g.createLinearGradient(0,0,0,38);
      grad.addColorStop(0, color + '33');
      grad.addColorStop(1, color + '00');
      new Chart(ctx, {
        type: 'line',
        data: { 
          labels: data.map((_,i)=>i), 
          datasets: [{ data, borderColor: color, borderWidth: 2, backgroundColor: grad, fill: true, tension: 0.45, pointRadius: 0 }] 
        },
        options: { 
          responsive: true, maintainAspectRatio: false, 
          plugins: { legend: { display: false }, tooltip: { enabled: false } }, 
          scales: { x: { display: false }, y: { display: false } }, 
          animation: { duration: 1000 } 
        }
      });
    } catch(e) { console.error("Sparkline error:", e); }
  }

  async function updateMainChart() {
    const metricBtn = document.querySelector('.db-tab.on');
    const periodBtn = document.querySelector('.period-btn.on');
    const metric = metricBtn ? metricBtn.dataset.metric : 'vistas';
    const period = periodBtn ? periodBtn.dataset.period : 'month';
    
    const ctx = document.getElementById('mainChart');
    if (!ctx) return;

    const sub = document.getElementById('chartSub');
    const labelsSuffix = { day: 'últimos 14 días', week: 'últimas 10 semanas', month: 'últimos 12 meses' };
    if (sub) sub.innerText = `Análisis de los ${labelsSuffix[period]}`;

    try {
      const resp = await fetch(`/vendedor/api/stats/chart?period=${period}&metric=${metric}`);
      const data = await resp.json();
      
      const config = {
        vistas: { label: 'Vistas', color: '#FF6A00' },
        publicaciones: { label: 'Post', color: '#3B82F6' },
        favoritos: { label: 'Favoritos', color: '#EF4444' }
      };
      const active = config[metric] || config.vistas;
      
      const g = ctx.getContext('2d');
      const grad = g.createLinearGradient(0, 0, 0, 350);
      grad.addColorStop(0, active.color + '44');
      grad.addColorStop(1, active.color + '00');

      if (mainChart) mainChart.destroy();
      mainChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: active.label, data: data.values,
            borderColor: active.color, borderWidth: 3, backgroundColor: grad,
            fill: true, tension: 0.4, pointRadius: period === 'day' ? 3 : 5, 
            pointHoverRadius: 8, pointBackgroundColor: '#fff', 
            pointBorderColor: active.color, pointBorderWidth: 2
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { intersect: false, mode: 'index' },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(17,24,39,.95)', titleFont: { family: 'Inter', size: 13, weight: '700' },
              bodyFont: { family: 'Inter', size: 12 }, padding: 12, cornerRadius: 10,
              callbacks: { label: c => '  ' + active.label + ': ' + c.raw.toLocaleString() }
            }
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: tickerColor(), font: { family: 'Inter', size: 10 } } },
            y: { 
              beginAtZero: true, grid: { color: gridColor(), drawBorder: false }, 
              ticks: { color: tickerColor(), font: { family: 'Inter', size: 10 } } 
            }
          },
          animation: { duration: 1200, easing: 'easeOutQuart' }
        }
      });
    } catch (e) { 
      console.error("Error al cargar gráfico:", e); 
      showToast("Error al cargar datos del gráfico", "error");
    }
  }

  async function updateInventoryChart() {
    const ctx = document.getElementById('inventoryChart');
    if (!ctx) return;
    try {
      const resp = await fetch('/vendedor/api/stats/distribution');
      const data = await resp.json();
      
      if (inventoryChart) inventoryChart.destroy();
      inventoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: data.labels,
          datasets: [{ data: data.values, backgroundColor: data.colors, borderWidth: 0, hoverOffset: 12 }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '75%',
          plugins: { legend: { display: false } },
          animation: { animateRotate: true, duration: 1500 }
        }
      });

      const legend = document.getElementById('inventoryLegend');
      if (legend && data.labels.length) {
        legend.innerHTML = data.labels.map((l, i) => `
          <div class="db-legend-row" style="margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div class="db-legend-lbl" style="display:flex; align-items:center; font-size:0.85rem; color:var(--t2);">
              <div class="db-legend-dot" style="background:${data.colors[i]};"></div>${l}
            </div>
            <div class="db-legend-val" style="font-weight:700; color:var(--t1);">${data.values[i]}</div>
          </div>
        `).join('');
      } else if (legend) {
        legend.innerHTML = '<p style="text-align:center; color:var(--t3); font-size:0.85rem;">Sin datos de inventario</p>';
      }
    } catch(e) { console.error("Update chart error", e); }
  }

  // ── LIVE ACTIVITY FEED (Auto Refresh 5s) ──
  let lastActivityId = null;
  
  async function updateActivityFeed() {
    const list = document.getElementById('dbActList');
    if(!list) return;

    try {
        const resp = await fetch('/vendedor/api/stats/activity');
        const data = await resp.json();
        if(!data || !data.length) return;

        const currentTopId = data[0].titulo + data[0].detalle + data[0].fecha_texto;
        if(lastActivityId && lastActivityId === currentTopId) return;
        
        let html = '';
        data.forEach((item, index) => {
            const isNew = lastActivityId && index === 0;
            html += `
              <div class="act-item ${isNew ? 'act-new' : ''}" data-id="${item.titulo}-${item.fecha_texto}">
                <div class="act-dot" style="background: ${item.color_bg}; color: ${item.color};">
                  <i class="${item.icono}"></i>
                </div>
                <div class="act-text">
                  <div class="at-title">${item.titulo}</div>
                  <div class="at-desc">${item.detalle}</div>
                  <div class="at-time"><i class="far fa-clock"></i> ${item.fecha_texto}</div>
                </div>
              </div>
            `;
        });
        
        list.innerHTML = html;
        lastActivityId = currentTopId;

        setTimeout(() => {
          const news = list.querySelectorAll('.act-new');
          news.forEach(el => el.classList.remove('act-new'));
        }, 2000);

    } catch (e) {
        console.error("Error updating activity feed:", e);
    }
  }

  setInterval(() => {
    updateActivityFeed().catch(e => {});
  }, 5000);

  // ── HELPERS ──
  function gridColor() { return getComputedStyle(root).getPropertyValue('--bd').trim() || 'rgba(0,0,0,0.05)'; }
  function tickerColor() { return getComputedStyle(root).getPropertyValue('--t2').trim() || '#6B7280'; }

  window.syncPrice = function(vid, price) {
    if(!vid || vid === 'null') return showToast("Selecciona un vehículo primero.", "error");
    activeVid = vid;
    activeValue = price;

    document.getElementById('modalTitle').innerText = "Sincronización Inteligente";
    document.getElementById('modalDesc').innerHTML = `¿Ajustar precio al promedio sugerido del mercado?<br aria-hidden="true"><strong style="color:var(--pr);font-size:1.1rem;">NUEVO PRECIO: $${price.toLocaleString()}</strong>`;
    document.getElementById('modalIcon').innerHTML = '<i class="fas fa-magic"></i>';
    document.getElementById('modalIcon').style.background = "rgba(255,106,0,0.1)";
    modalInputContainer.style.display = 'none';
    
    openModal(() => updatePriceAJAX(activeVid, activeValue));
  };

  window.editManual = function(vid, current) {
    if(!vid || vid === 'null') return showToast("Selecciona un vehículo primero.", "error");
    activeVid = vid;
    
    document.getElementById('modalTitle').innerText = "Ajuste Profesional";
    document.getElementById('modalDesc').innerText = "Ingresa el valor exacto que deseas establecer para este vehículo.";
    document.getElementById('modalIcon').innerHTML = '<i class="fas fa-edit"></i>';
    document.getElementById('modalIcon').style.background = "rgba(59,130,246,0.1)";
    modalInputContainer.style.display = 'block';
    modalInput.value = current;
    
    openModal(() => {
      const val = modalInput.value;
      if(val && !isNaN(val)) updatePriceAJAX(activeVid, val);
      else showToast("Ingresa un precio válido", "error");
    });
  };

  function openModal(confirmCallback) {
    modal.classList.add('active');
    modalBtnConfirm.onclick = () => { confirmCallback(); closeModal(); };
    modalBtnCancel.onclick = closeModal;
  }

  function closeModal() { modal.classList.remove('active'); }

  function updatePriceAJAX(vid, newPrice) {
    const formData = new FormData();
    formData.append('precio', newPrice);
    fetch(`/vendedor/vehiculo/${vid}/actualizar-precio`, { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      if(data.success) {
        showToast("¡Precio actualizado de forma profesional!", "success");
        setTimeout(() => window.location.reload(), 1500);
      } else {
        showToast("Error estratégico: " + data.error, "error");
      }
    }).catch(() => showToast("Fallo de conexión", "error"));
  }

  function showToast(msg, type = "success") {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast-pro';
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}" style="color:${type === 'success' ? '#10B981' : '#EF4444'}"></i><span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 400); }, 3500);
  }

  window.exportDashboard = function() { showToast("Exportando informe estratégico...", "success"); };

  // ── INIT ON DOM READY ──
  document.addEventListener('DOMContentLoaded', () => {
    const counters = document.querySelectorAll('[data-count]');
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) { animateCount(e.target); obs.unobserve(e.target); } });
    }, { threshold: 0.3 });
    counters.forEach(el => obs.observe(el));

    setTimeout(() => {
      try { updateMainChart(); } catch(e){}
      try { updateInventoryChart(); } catch(e){}
      try { updateActivityFeed(); } catch(e){}
  
      try { sparkline('sk1', [12,19,15,25,22,28,32,35,38,32,45,40], '#FF6A00'); } catch(e){}
      try { sparkline('sk2', [20,25,22,30,28,35,38,32,40,42,45,50], '#3B82F6'); } catch(e){}
      // Favoritos removido por rediseño
      try { sparkline('sk4', [10,12,11,14,13,15,15,16,18,20,19,22], '#8B5CF6'); } catch(e){}
      try { sparkline('sk5', [5,8,12,10,15,14,18,20,22,18,25,30], '#25D366'); } catch(e){}
    }, 500);

    document.querySelectorAll('.db-tab').forEach(btn => {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.db-tab').forEach(t => t.classList.remove('on'));
        this.classList.add('on');
        updateMainChart();
      });
    });

    document.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('on'));
        this.classList.add('on');
        updateMainChart();
      });
    });

    const notifBtn = document.getElementById('notifBtn');
    const dropdown = document.getElementById('notifDropdown');
    if(notifBtn && dropdown) {
      notifBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
      });
      document.addEventListener('click', () => { if(dropdown) dropdown.style.display = 'none'; });
    }

    setTimeout(() => {
      document.querySelectorAll('.goal-fill[data-width]').forEach(el => {
        el.style.width = el.dataset.width + '%';
      });
    }, 400);
  });

})();
