document.addEventListener("DOMContentLoaded", () => {
    let currentStep = 1;
    const totalSteps = 5;
    
    const btnNext = document.getElementById('btnNext');
    const btnPrev = document.getElementById('btnPrev');
    const btnSubmit = document.getElementById('btnSubmit');

    function updateView() {
        document.querySelectorAll('.pv-step-view').forEach(el => el.classList.remove('active'));
        document.getElementById(`step${currentStep}`).classList.add('active');
        
        btnPrev.style.visibility = currentStep === 1 ? 'hidden' : 'visible';
        
        if (currentStep === totalSteps) {
            btnNext.style.display = 'none';
            btnSubmit.classList.add('active');
        } else {
            btnNext.style.display = 'block';
            btnSubmit.classList.remove('active');
        }
        
        for (let i = 1; i <= totalSteps; i++) {
            const indicator = document.getElementById(`stepIndicator${i}`);
            const line = document.getElementById(`line${i}`);
            
            indicator.classList.remove('active', 'completed');
            if (line) {
                line.classList.remove('solid');
                line.style.backgroundImage = 'linear-gradient(to right, var(--line-dash) 50%, transparent 50%)';
            }
            if (i === currentStep) {
                indicator.classList.add('active');
                if(line) line.style.backgroundImage = 'linear-gradient(to right, var(--line-dash) 50%, transparent 50%)';
            } else if (i < currentStep) {
                indicator.classList.add('completed');
                if(line) {
                    line.classList.add('solid');
                    line.style.backgroundImage = 'none';
                }
            }
        }
        
        const stepText = document.getElementById('stepIndicatorText');
        if (stepText) stepText.textContent = `Paso ${currentStep} de ${totalSteps}`;
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ==========================================
    // ✅ LÓGICA DE SELECTORES EN CASCADA
    // ==========================================
    const tipoSelect = document.getElementById('tipo');
    const marcaSelect = document.getElementById('marca');
    const modeloSelect = document.getElementById('modelo');
    const divOtroModelo = document.getElementById('div-otro-modelo');
    const inputOtroModelo = document.getElementById('otro_modelo');

    // --- Campo para escribir marca manualmente ---
    let divOtraMarca = document.getElementById('div-otra-marca');
    let inputOtraMarca = document.getElementById('otra_marca');

    // Crear el campo de marca manual si no existe en el HTML
    if (!divOtraMarca) {
        divOtraMarca = document.createElement('div');
        divOtraMarca.id = 'div-otra-marca';
        divOtraMarca.className = 'pv-group';
        divOtraMarca.style.cssText = 'display:none; margin-top: -8px; margin-bottom: 24px; animation: fadeInView 0.3s ease forwards;';
        divOtraMarca.innerHTML = `
            <label for="otra_marca" style="color: var(--o);"><i class="fas fa-pen"></i> Escribe la marca <span class="req">*</span></label>
            <input type="text" id="otra_marca" name="otra_marca" class="pv-input"
                placeholder="Ej: Kia, BYD, Chery..." style="border-color: var(--o);">
        `;
        // Insertarlo después del wrap de marcaSelect
        marcaSelect.closest('.pv-group').insertAdjacentElement('afterend', divOtraMarca);
        inputOtraMarca = document.getElementById('otra_marca');
    }

    tipoSelect.addEventListener('change', function() {
        const tipoId = this.value;

        marcaSelect.innerHTML = '<option value="" disabled selected>Cargando marcas...</option>';
        marcaSelect.disabled = true;
        modeloSelect.innerHTML = '<option value="" disabled selected>Primero seleccione la marca...</option>';
        modeloSelect.disabled = true;

        divOtroModelo.style.display = 'none';
        inputOtroModelo.required = false;
        inputOtroModelo.value = '';
        divOtraMarca.style.display = 'none';
        inputOtraMarca.required = false;
        inputOtraMarca.value = '';

        if (!tipoId) return;

        fetch('/obtener_marcas/' + tipoId)
            .then(r => r.json())
            .then(data => {
                marcaSelect.innerHTML = '<option value="" disabled selected>Seleccione la marca...</option>';
                data.forEach(m => {
                    marcaSelect.innerHTML += `<option value="${m.id}">${m.nombre}</option>`;
                });
                // Opción "Otra" al final
                marcaSelect.innerHTML += `<option value="otra" style="font-weight:800;color:var(--o);">+ Otra (Escribir manualmente)</option>`;
                marcaSelect.disabled = false;
            })
            .catch(() => {
                marcaSelect.innerHTML = '<option value="" disabled selected>Error al cargar. Intente de nuevo.</option>';
            });
    });

    marcaSelect.addEventListener('change', function() {
        const marcaId = this.value;

        // Resetear modelo
        modeloSelect.innerHTML = '<option value="" disabled selected>Cargando modelos...</option>';
        modeloSelect.disabled = true;
        divOtroModelo.style.display = 'none';
        inputOtroModelo.required = false;
        inputOtroModelo.value = '';

        // Mostrar/ocultar campo de marca manual
        if (marcaId === 'otra') {
            divOtraMarca.style.display = 'flex';
            inputOtraMarca.required = true;
            setTimeout(() => inputOtraMarca.focus(), 100);
            // Para marca manual, mostrar directo el campo de modelo manual
            modeloSelect.innerHTML = '<option value="otro" selected>+ Escribe el modelo manualmente</option>';
            divOtroModelo.style.display = 'flex';
            inputOtroModelo.required = true;
            modeloSelect.disabled = false;
            return;
        } else {
            divOtraMarca.style.display = 'none';
            inputOtraMarca.required = false;
            inputOtraMarca.value = '';
        }

        if (!marcaId) return;

        fetch('/obtener_modelos/' + marcaId)
            .then(r => r.json())
            .then(data => {
                modeloSelect.innerHTML = '<option value="" disabled selected>Seleccione el modelo...</option>';
                data.forEach(m => {
                    modeloSelect.innerHTML += `<option value="${m.id}">${m.nombre}</option>`;
                });
                modeloSelect.innerHTML += `<option value="otro" style="font-weight:800;color:var(--o);">+ Otro (Escribir manualmente)</option>`;
                modeloSelect.disabled = false;
            })
            .catch(() => {
                modeloSelect.innerHTML = '<option value="" disabled selected>Error al cargar. Intente de nuevo.</option>';
            });
    });

    modeloSelect.addEventListener('change', function() {
        if (this.value === 'otro') {
            divOtroModelo.style.display = 'flex';
            inputOtroModelo.required = true;
            setTimeout(() => inputOtroModelo.focus(), 100);
        } else {
            divOtroModelo.style.display = 'none';
            inputOtroModelo.required = false;
            inputOtroModelo.value = '';
        }
    });

    function validateStep() {
        const view = document.getElementById(`step${currentStep}`);
        let inputs = view.querySelectorAll('input[required], select[required], textarea[id="descripcion"]');
        let isValid = true;
        
        if(currentStep === 5) {
            if(dt.items.length === 0) {
                isValid = false;
                document.querySelector('.pv-upload-box').style.borderColor = '#ef4444';
            } else {
                document.querySelector('.pv-upload-box').style.borderColor = 'var(--line)';
            }
        }
        
        inputs.forEach(input => {
            if(input.type === 'file') return;
            if (!input.value.trim()) {
                isValid = false;
                input.style.borderColor = '#ef4444';
            } else {
                input.style.borderColor = 'var(--line)';
            }
        });
        
        if (!isValid) {
            if(currentStep===5) alert("Sube al menos 1 imagen.");
            else alert("Por favor, completa los campos requeridos enmarcados en rojo.");
        }
        return isValid;
    }

    btnNext.addEventListener('click', () => {
        if (validateStep()) {
            currentStep++;
            updateView();
        }
    });
    
    btnPrev.addEventListener('click', () => {
        currentStep--;
        updateView();
    });
    
    updateView();
    
    // ==========================================
    // ✅ FORMATEADOR DE PRECIOS (COP)
    // ==========================================
    const precioVisual = document.getElementById('precio_visual');
    const precioOculto = document.getElementById('precio');

    if (precioVisual) {
        precioVisual.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, "");
            if (value) {
                precioOculto.value = value;
                e.target.value = new Intl.NumberFormat('es-CO', {
                    style: 'decimal',
                    minimumFractionDigits: 0
                }).format(value);
            } else {
                precioOculto.value = "";
                e.target.value = "";
            }
        });
    }
    
    // ==========================================
    // ✅ LOGIC PARA FOTOS & DRAG-DROP
    // ==========================================
    const fileInput = document.getElementById('imagenesInput');
    const previewArea = document.getElementById('previewArea');
    const uploadBox = document.getElementById('uploadBox');
    let dt = new DataTransfer();
    
    function updateFileCount() {
        const fc = document.getElementById('fileCount');
        if(fc) fc.textContent = `${dt.items.length} archivo${dt.items.length === 1 ? '' : 's'} seleccionado${dt.items.length === 1 ? '' : 's'}`;
        calculateSeoMeter();
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const files = e.target.files;
            if (dt.items.length + files.length > 20) {
                alert("Has superado el límite de 20 imágenes.");
                return;
            }
            
            Array.from(files).forEach(file => {
                dt.items.add(file);
                const reader = new FileReader();
                reader.onload = (event) => {
                    const card = document.createElement('div');
                    card.className = 'pv-img-wrap';
                    card.innerHTML = `
                        <img src="${event.target.result}" class="pv-img">
                        <button type="button" class="pv-img-del"><i class="fas fa-trash"></i></button>
                    `;
                    
                    card.querySelector('.pv-img-del').addEventListener('click', () => {
                        card.remove();
                        let index = -1;
                        for(let i=0; i<dt.items.length; i++){
                            if(dt.files[i].name === file.name) index = i;
                        }
                        if(index!==-1){
                            let newDt = new DataTransfer();
                            Array.from(dt.files).forEach((f, i) => { if (i !== index) newDt.items.add(f); });
                            dt = newDt;
                            fileInput.files = dt.files;
                        }
                        updateFileCount();
                        if(dt.items.length === 0 && uploadBox) uploadBox.style.borderColor = 'var(--line)';
                    });
                    
                    previewArea.appendChild(card);
                };
                reader.readAsDataURL(file);
            });
            fileInput.files = dt.files;
            updateFileCount();
            if(dt.items.length > 0 && uploadBox) uploadBox.style.borderColor = 'var(--line)';
        });
    }

    if (uploadBox) {
        uploadBox.addEventListener('dragover', e => {
            e.preventDefault();
            uploadBox.style.borderColor = 'var(--o)';
        });
        uploadBox.addEventListener('dragleave', () => {
            uploadBox.style.borderColor = 'var(--line)';
        });
        uploadBox.addEventListener('drop', e => {
            e.preventDefault();
            uploadBox.style.borderColor = 'var(--line)';
            if(e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }
    
    // ==========================================
    // ✅ SEO METER GAMIFICATION
    // ==========================================
    const descInput = document.getElementById('descripcion');
    if(descInput) descInput.addEventListener('input', calculateSeoMeter);
    
    function calculateSeoMeter() {
        const progress = document.getElementById('seo-progress');
        const label = document.getElementById('seo-label');
        if(!progress || !label) return;
        
        let score = 0;
        if(currentStep > 1) score += 20; // Al menos pasó el paso 1
        let pOculto = document.getElementById('precio');
        if(pOculto && pOculto.value) score += 20; // Puso precio
        
        if(descInput) {
            const words = descInput.value.trim().split(/\s+/).filter(w => w.length > 1).length;
            if(words > 5) score += 10;
            if(words > 20) score += 20;
        }
        
        if(dt.items.length >= 1) score += 10;
        if(dt.items.length >= 5) score += 20;
        
        // Asignar UI
        progress.style.width = `${Math.min(score, 100)}%`;
        if(score < 40) {
            progress.style.background = '#ef4444';
            label.textContent = 'Pobre';
            label.style.background = '#ef4444';
        } else if(score < 80) {
            progress.style.background = '#F59E0B';
            label.textContent = 'Bueno';
            label.style.background = '#F59E0B';
        } else {
            progress.style.background = '#10b981';
            label.textContent = 'Excelente';
            label.style.background = '#10b981';
        }
    }

    // ==========================================
    // ✅ AUTO-SAVE LOCALSTORAGE AISLADO POR USUARIO
    // ==========================================
    function getDraftKey() {
        const userSpan = document.querySelector('.user-name');
        const userName = userSpan ? userSpan.textContent.trim().replace(/[^a-zA-Z0-9]/g, '') : 'guest';
        return `vender_draft_${userName}`;
    }
    const DRAFT_KEY = getDraftKey();
    const formInputs = document.querySelectorAll('input:not([type="file"]), select, textarea');
    
    function saveDraft() {
        const draft = {};
        formInputs.forEach(inp => {
            if(inp.name && inp.type !== 'file' && inp.type !== 'hidden') {
                if(inp.type === 'checkbox') {
                    if(!draft[inp.name]) draft[inp.name] = [];
                    if(inp.checked) draft[inp.name].push(inp.value);
                } else if(inp.type === 'radio') {
                    if(inp.checked) draft[inp.name] = inp.value;
                } else {
                    draft[inp.name] = inp.value;
                }
            }
        });
        localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    }
    
    function loadDraft() {
        const saved = localStorage.getItem(DRAFT_KEY);
        if(saved) {
            try {
                const draft = JSON.parse(saved);
                const cascadeKeys = ['tipo', 'marca', 'modelo', 'otra_marca', 'otro_modelo'];
                
                Object.keys(draft).forEach(key => {
                    if (cascadeKeys.includes(key)) return; // Se manejarán asíncronamente
                    
                    const inps = document.querySelectorAll(`[name="${key}"]:not([type="hidden"])`);
                    if(inps.length === 1 && inps[0].type !== 'checkbox' && inps[0].type !== 'radio') {
                        if(inps[0].value === '') inps[0].value = draft[key];
                    } else if(inps.length > 0 && Array.isArray(draft[key])) {
                        inps.forEach(inp => {
                            if(inp.type === 'checkbox' && draft[key].includes(inp.value)) inp.checked = true;
                        });
                    }
                });
                
                if(draft['precio'] && precioVisual) {
                    precioVisual.value = draft['precio'];
                    precioVisual.dispatchEvent(new Event('input'));
                }
                setTimeout(calculateSeoMeter, 500);
                
                // 🚀 Restauración Asíncrona (Promesas) para Cascada
                async function restoreCascade() {
                    const waitForEnable = (selectEl) => {
                        return new Promise(resolve => {
                            let interval = setInterval(() => {
                                if(!selectEl.disabled) {
                                    clearInterval(interval);
                                    resolve();
                                }
                            }, 50);
                            setTimeout(() => { clearInterval(interval); resolve(); }, 3000); // 3s max
                        });
                    };

                    if(draft['tipo']) {
                        const tSel = document.getElementById('tipo');
                        if(tSel) {
                            tSel.value = draft['tipo'];
                            tSel.dispatchEvent(new Event('change'));
                            
                            if(draft['marca']) {
                                const mSel = document.getElementById('marca');
                                await waitForEnable(mSel);
                                mSel.value = draft['marca'];
                                mSel.dispatchEvent(new Event('change'));
                                
                                if(draft['marca'] === 'otra') {
                                    setTimeout(() => {
                                        if(draft['otra_marca']) document.getElementById('otra_marca').value = draft['otra_marca'];
                                        if(draft['otro_modelo']) document.getElementById('otro_modelo').value = draft['otro_modelo'];
                                    }, 150);
                                    return;
                                }
                                
                                if(draft['modelo']) {
                                    const modSel = document.getElementById('modelo');
                                    await waitForEnable(modSel);
                                    modSel.value = draft['modelo'];
                                    modSel.dispatchEvent(new Event('change'));
                                    
                                    if(draft['modelo'] === 'otro' && draft['otro_modelo']) {
                                        setTimeout(() => {
                                            document.getElementById('otro_modelo').value = draft['otro_modelo'];
                                        }, 150);
                                    }
                                }
                            }
                        }
                    }
                }
                
                restoreCascade();
                
            } catch(e) { console.error("Error cargando draft:", e); }
        }
    }
    
    formInputs.forEach(inp => {
        inp.addEventListener('input', saveDraft);
        inp.addEventListener('change', saveDraft);
    });
    
    // Cargar el draft cuando se obtienen los datos asincrónicos
    window.addEventListener('load', loadDraft);
    
    document.getElementById('venderForm').addEventListener('submit', function(e) {
        if(!validateStep()){
           e.preventDefault();
        } else {
           localStorage.removeItem(DRAFT_KEY); // Limpiar draft si todo salió bien
        }
    });
});
