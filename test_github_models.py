# test_github_models.py - Test de GitHub Models AI
import os
from dotenv import load_dotenv
import requests
import json

# Cargar variables de entorno
load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_MODEL = os.getenv('GITHUB_MODEL', 'gpt-4o')

print("=" * 60)
print("🧪 TEST - GitHub Models AI")
print("=" * 60)

# Verificar que el token esté configurado
if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN no está configurado en .env")
    exit(1)

print(f"\n✅ Token encontrado")
print(f"📦 Modelo: {GITHUB_MODEL}")

# Hacer una prueba simple
print(f"\n📤 Enviando solicitud a GitHub Models...")

url = "https://models.inference.ai.azure.com/chat/completions"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "model": GITHUB_MODEL,
    "messages": [
        {
            "role": "system",
            "content": "Eres un asistente amable. Responde en español brevemente."
        },
        {
            "role": "user",
            "content": "Hola, ¿quién eres y qué puedes hacer?"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 512
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 200:
        print("✅ Conexión exitosa!")
        data = response.json()
        
        respuesta = data["choices"][0]["message"]["content"]
        tokens_usados = data.get("usage", {}).get("total_tokens", "N/A")
        
        print(f"\n📨 Respuesta del modelo:")
        print("-" * 60)
        print(respuesta)
        print("-" * 60)
        print(f"\n📊 Tokens usados: {tokens_usados}")
        print("\n✅ ¡GitHub Models funciona correctamente!")
        
    else:
        print(f"❌ Error HTTP {response.status_code}")
        print(f"Respuesta: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Error: Tiempo de espera agotado (timeout)")
except requests.exceptions.ConnectionError:
    print("❌ Error: No se pudo conectar a la API")
except Exception as e:
    print(f"❌ Error inesperado: {e}")

print("\n" + "=" * 60)

