// static/js/test.js
console.log("✅ test.js cargado");

document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ DOM cargado");
    
    const sendBtn = document.getElementById('send-message');
    const input = document.getElementById('user-input');
    
    console.log("Botón enviar:", sendBtn);
    console.log("Input:", input);
    
    if (sendBtn) {
        sendBtn.addEventListener('click', function() {
            alert('¡Botón funcionando!');
        });
    }
});