/**
 * Drive Market - Listing Tools
 * Handles AI Description Generation, SEO Scoring, and Image Optimization.
 */

document.addEventListener('DOMContentLoaded', () => {
    const btnIA = document.getElementById('btn-generar-ia');
    const descTextarea = document.getElementById('descripcion');
    const seoProgress = document.getElementById('seo-progress');
    const seoLabel = document.getElementById('seo-label');

    // --- AI Description Generator ---
    if (btnIA && descTextarea) {
        btnIA.addEventListener('click', async () => {
            // Collect data from the form
            const marca = document.getElementById('marca').options[document.getElementById('marca').selectedIndex]?.text;
            const modeloId = document.getElementById('modelo').value;
            let modelo = document.getElementById('modelo').options[document.getElementById('modelo').selectedIndex]?.text;
            
            if (modeloId === 'otro') {
                modelo = document.getElementById('otro_modelo').value;
            }

            const anio = document.getElementById('anio').value;
            const kilometraje = document.getElementById('kilometraje').value;
            const version = document.getElementById('version').value;
            const ciudad = document.getElementById('ciudad_venta').value;
            
            // Collect checked features
            const extras = Array.from(document.querySelectorAll('input[name="caracteristicas"]:checked'))
                .map(cb => cb.parentElement.querySelector('.pub-chk-txt').textContent);

            if (!marca || !modelo || !anio) {
                alert('Por favor completa la Marca, Modelo y Año en los pasos anteriores para generar una descripción precisa.');
                return;
            }

            // UI State: Loading
            btnIA.disabled = true;
            const originalContent = btnIA.innerHTML;
            btnIA.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
            descTextarea.placeholder = 'La IA de Drive Market está redactando tu anuncio...';

            try {
                const response = await fetch('/vendedor/generar_descripcion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ marca, modelo, anio, kilometraje, version, extras, ciudad })
                });

                const result = await response.json();

                if (result.ok) {
                    descTextarea.value = result.descripcion;
                    updateSEOScore();
                    // Smooth scroll to the textarea
                    descTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    alert('Error: ' + result.msg);
                }
            } catch (error) {
                console.error('AI Error:', error);
                alert('Ocurrió un error al conectar con el servicio de IA.');
            } finally {
                btnIA.disabled = false;
                btnIA.innerHTML = originalContent;
                descTextarea.placeholder = 'Describe tu vehículo...';
            }
        });
    }

    // --- SEO Score Meter ---
    const inputsToTrack = ['marca', 'modelo', 'anio', 'precio', 'descripcion', 'imagenesInput', 'caracteristicas'];
    
    function updateSEOScore() {
        if (!seoProgress) return;

        let score = 0;
        
        // 1. Basic Data (Step 1 & 2)
        if (document.getElementById('marca').value) score += 10;
        if (document.getElementById('modelo').value) score += 10;
        if (document.getElementById('anio').value) score += 10;
        if (document.getElementById('precio').value > 0) score += 10;
        
        // 2. Description (Step 3)
        const descLength = descTextarea?.value.length || 0;
        if (descLength > 50) score += 15;
        if (descLength > 200) score += 10;

        // 3. Features (Step 3)
        const featuresCount = document.querySelectorAll('input[name="caracteristicas"]:checked').length;
        if (featuresCount >= 3) score += 10;
        if (featuresCount >= 8) score += 5;

        // 4. Photos (Step 4) - We use the global 'dt' from the template if available
        // Or we check the preview Area children
        const photosCount = document.getElementById('previewArea')?.children.length || 0;
        if (photosCount >= 1) score += 10;
        if (photosCount >= 5) score += 10;
        if (photosCount >= 10) score += 10;

        // Caps score at 100
        score = Math.min(100, score);

        // Update UI
        seoProgress.style.width = score + '%';
        
        if (score < 40) {
            seoProgress.style.backgroundColor = '#ef4444';
            seoLabel.textContent = 'Pobre';
        } else if (score < 75) {
            seoProgress.style.backgroundColor = '#f59e0b';
            seoLabel.textContent = 'Bueno';
        } else {
            seoProgress.style.backgroundColor = '#10b981';
            seoLabel.textContent = 'Excelente';
        }
    }

    // Listen to changes
    document.addEventListener('input', (e) => {
        if (inputsToTrack.some(id => e.target.id === id || e.target.name === id)) {
            updateSEOScore();
        }
    });

    // Initial check
    setTimeout(updateSEOScore, 500);
});
