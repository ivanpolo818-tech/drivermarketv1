// static/js/chatbot.js
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Chatbot inicializado");
    
    // Elementos del DOM
    const messagesContainer = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-message');
    const clearButton = document.getElementById('clear-chat');
    const humanButton = document.getElementById('contact-human');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Verificar que los elementos existen
    console.log("Elementos encontrados:", {
        messagesContainer: !!messagesContainer,
        userInput: !!userInput,
        sendButton: !!sendButton
    });
    
    if (!sendButton || !userInput) {
        console.error("❌ No se encontraron los elementos del chat");
        return;
    }
    
    // Event Listeners
    sendButton.addEventListener('click', function(e) {
        console.log("🖱️ Click en enviar");
        sendMessage();
    });
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            console.log("⏎ Enter presionado");
            e.preventDefault();
            sendMessage();
        }
    });
    
    if (clearButton) {
        clearButton.addEventListener('click', clearChat);
    }
    
    if (humanButton) {
        humanButton.addEventListener('click', contactHuman);
    }
    
    // Cargar FAQs al iniciar
    loadFAQs();
    
    // Función para enviar mensaje
    async function sendMessage() {
        const message = userInput.value.trim();
        console.log("📨 Enviando mensaje:", message);
        
        if (!message) {
            console.log("⚠️ Mensaje vacío");
            return;
        }
        
        // Mostrar mensaje del usuario
        addMessage(message, 'user');
        userInput.value = '';
        
        // Mostrar indicador de escritura
        showTypingIndicator();
        
        try {
            console.log("📡 Enviando a /api/chat...");
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            console.log("📥 Respuesta recibida:", response.status);
            
            const data = await response.json();
            console.log("📊 Datos:", data);
            
            // Ocultar indicador de escritura
            hideTypingIndicator();
            
            if (data.respuesta) {
                addMessage(data.respuesta, 'bot');
                
                // Mostrar sugerencias de vehículos si existen
                if (data.sugerencias && data.sugerencias.length > 0) {
                    console.log(`✨ Mostrando ${data.sugerencias.length} sugerencias`);
                    addVehicleSuggestions(data.sugerencias);
                }
                
                if (data.conversacion_id) {
                    addFeedbackButtons(data.conversacion_id);
                }
            } else if (data.error) {
                addMessage('Error: ' + data.error, 'bot');
            }
            
        } catch (error) {
            console.error('❌ Error:', error);
            hideTypingIndicator();
            addMessage('Error de conexión. ¿Está el servidor corriendo?', 'bot');
        }
    }
    
    function addMessage(text, sender, isHtml = false) {
        console.log(`➕ Añadiendo mensaje ${sender}:`, text.substring(0, 30));
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        if (isHtml) {
            messageDiv.innerHTML = text;
        } else {
            messageDiv.textContent = text;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function addVehicleSuggestions(vehiculos) {
        console.log(`🚗 Mostrando ${vehiculos.length} sugerencias de vehículos`);
        
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'vehicle-suggestions';
        suggestionsDiv.innerHTML = '<div class="suggestions-title">🚗 Vehículos que te podrían interesar:</div>';
        
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'suggestions-grid';
        
        vehiculos.forEach(v => {
            const card = document.createElement('div');
            card.className = 'suggestion-card';
            card.innerHTML = `
                <div class="suggestion-image">
                    <img src="${'/static/' + v.imagen}" alt="${v.marca} ${v.modelo}" onerror="this.src='/static/img/default_car.jpg'">
                </div>
                <div class="suggestion-info">
                    <div class="suggestion-title">${v.marca} ${v.modelo}</div>
                    <div class="suggestion-year">${v.anio}</div>
                    <div class="suggestion-details">
                        <span>💰 $${v.precio}</span><br>
                        <span>📏 ${v.km} km</span>
                    </div>
                    <a href="/detalles/${v.id}" target="_blank" class="suggestion-link">Ver detalle →</a>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
        
        suggestionsDiv.appendChild(cardsContainer);
        messagesContainer.appendChild(suggestionsDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'flex';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'none';
        }
    }
    
    function clearChat() {
        console.log("🧹 Limpiando chat");
        messagesContainer.innerHTML = `
            <div class="message bot-message">
                ¡Hola! Soy el asistente virtual de Drivemarket. 
                ¿En qué puedo ayudarte hoy?
            </div>
        `;
    }
    
    function contactHuman() {
        console.log("👤 Contactar humano");
        addMessage('Me gustaría hablar con un agente humano', 'user');
        
        setTimeout(() => {
            addMessage(
                'Un agente te contactará pronto. Por favor, espera unos minutos.',
                'bot'
            );
        }, 1000);
    }
    
    async function loadFAQs() {
        console.log("📚 Cargando FAQs...");
        try {
            const response = await fetch('/api/faqs');
            const faqs = await response.json();
            console.log("✅ FAQs cargadas:", faqs.length);
            
            const faqList = document.getElementById('faq-list');
            if (faqList && faqs.length > 0) {
                faqList.innerHTML = '';
                faqs.forEach(faq => {
                    const item = document.createElement('div');
                    item.className = 'faq-item';
                    item.innerHTML = `
                        <div class="faq-question">${faq.pregunta}</div>
                        <div class="faq-answer">${faq.respuesta}</div>
                    `;
                    item.addEventListener('click', () => {
                        userInput.value = faq.pregunta;
                        sendMessage();
                    });
                    faqList.appendChild(item);
                });
            }
        } catch (error) {
            console.error('❌ Error cargando FAQs:', error);
        }
    }
    
    function addFeedbackButtons(conversacionId) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-buttons';
        feedbackDiv.innerHTML = `
            <span>¿Te fue útil?</span>
            <button onclick="sendFeedback(${conversacionId}, true)">👍 Sí</button>
            <button onclick="sendFeedback(${conversacionId}, false)">👎 No</button>
        `;
        messagesContainer.appendChild(feedbackDiv);
    }
});

// Función global para feedback
async function sendFeedback(conversacionId, util) {
    console.log(`📊 Feedback: ${conversacionId} = ${util ? '👍' : '👎'}`);
    try {
        await fetch('/api/chat/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                conversacion_id: conversacionId,
                util: util 
            })
        });
    } catch (error) {
        console.error('Error sending feedback:', error);
    }
}