# asistente_ia.py - Cerebro de IA para Drive Market (v2 - Inventario Real)
import os
import re
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from models import db, FAQ, Vehiculo, Marca, Modelo, ConversacionChatbot
import sqlalchemy
from flask import current_app

load_dotenv()

# Configuración de GitHub Models
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_MODEL = os.getenv('GITHUB_MODEL', 'gpt-4o')

# ── Caché de respuestas frecuentes (10 minutos de TTL) ──
_RESPONSE_CACHE: dict = {}
CACHE_TTL = 600  # segundos

def get_cached_response(key: str):
    """Devuelve la respuesta cacheada si no expiró, o None."""
    if key in _RESPONSE_CACHE:
        respuesta, ts = _RESPONSE_CACHE[key]
        import time
        if time.time() - ts < CACHE_TTL:
            print(f"⚡️  Cache HIT — {key[:8]}...")
            return respuesta
        del _RESPONSE_CACHE[key]
    return None

def set_cached_response(key: str, respuesta: str) -> None:
    """Almacena una respuesta en caché con timestamp actual."""
    import time
    # Limpiar entradas expiradas si el caché crece mucho
    if len(_RESPONSE_CACHE) > 200:
        now = time.time()
        expired = [k for k, (_, ts) in _RESPONSE_CACHE.items() if now - ts >= CACHE_TTL]
        for k in expired:
            del _RESPONSE_CACHE[k]
    _RESPONSE_CACHE[key] = (respuesta, time.time())
    print(f"✅ Cache SET — {key[:8]}... ({len(_RESPONSE_CACHE)} entradas)")

def detectar_intencion(mensaje):
    """
    Detecta si el usuario quiere COMPRAR, VENDER o tiene DUDAS.
    """
    mensaje_lower = mensaje.lower()
    
    palabras_comprar = ['comprar', 'buscar', 'quiero un', 'vendo', 'auto', 'coche', 'vehículo', 
                        'ando buscando', 'estoy buscando', 'me interesa', 'cuánto cuesta', 'precio',
                        'disponible', 'tiene', '¿qué autos', 'recomendación', 'recomienda']
    palabras_vender = ['vender', 'publicar', 'vender mi', 'mi coche', 'mi auto', 'mi vehículo',
                       'quiero vender', 'cómo publico', 'cómo vendo', 'necesito vender']
    palabras_dudas = ['cómo', 'por qué', '¿qué', 'ayuda', 'duda', 'problema', 'no sé', 'no entiendo']
    
    c_comprar = sum(1 for p in palabras_comprar if p in mensaje_lower)
    c_vender = sum(1 for p in palabras_vender if p in mensaje_lower)
    c_dudas = sum(1 for p in palabras_dudas if p in mensaje_lower)
    
    # Si menciona una marca específica, forzamos intención de compra
    marcas = ['toyota', 'nissan', 'honda', 'ford', 'chevrolet', 'hyundai', 'kia', 'volkswagen', 
              'mazda', 'renault', 'suzuki', 'jeep', 'bmw', 'mercedes', 'audi', 'subaru', 'mitsubishi']
    mencion_marca = any(m in mensaje_lower for m in marcas)
    
    if mencion_marca or (c_comprar >= c_vender and c_comprar >= c_dudas and c_comprar > 0):
        return {'intencion': 'comprar', 'confianza': 1.0 if mencion_marca else min(c_comprar / 1.5, 1.0)}
    elif c_vender > c_comprar and c_vender >= c_dudas:
        return {'intencion': 'vender', 'confianza': min(c_vender / 2, 1.0)}
    elif c_dudas > 0:
        return {'intencion': 'dudas', 'confianza': min(c_dudas / 3, 1.0)}
    return {'intencion': 'general', 'confianza': 0.5}

def extraer_parametros_busqueda(mensaje):
    """
    Extrae parámetros de búsqueda técnica del mensaje del usuario.
    """
    params = {}
    m_low = mensaje.lower()
    
    # Marcas comunes en Colombia
    marcas = ['toyota', 'nissan', 'honda', 'ford', 'chevrolet', 'hyundai', 'kia', 'volkswagen', 
              'mazda', 'renault', 'suzuki', 'jeep', 'bmw', 'mercedes', 'audi', 'subaru', 'mitsubishi']
    for m in marcas:
        if m in m_low:
            params['marca'] = m.capitalize()
            break
            
    # Año (ej: 2020, 2019)
    anio_match = re.search(r'\b(20\d{2}|19\d{2})\b', m_low)
    if anio_match:
        params['anio'] = int(anio_match.group(1))
        
    # Precio (ej: 50 millones, 50m, 150 mil)
    precio_match = re.search(r'(\d+)\s*(millones?|m|mill|millón)', m_low)
    if precio_match:
        valor = float(precio_match.group(1))
        params['precio_max'] = int(valor * 1_000_000)
    else:
        precio_match2 = re.search(r'(\d+)\s*(mil|k)\b', m_low)
        if precio_match2:
            valor = float(precio_match2.group(1))
            params['precio_max'] = int(valor * 1_000)
        
    return params

def buscar_vehiculos_ia(params, limite=4):
    """
    Realiza búsqueda real en la base de datos, obteniendo la primera imagen de cada vehículo.
    """
    try:
        import sqlalchemy
        # Subquery para obtener la primera imagen de cada vehículo
        imagen_subq = sqlalchemy.text("SELECT MIN(url_imagen) FROM imagenes_vehiculos WHERE id_vehiculo = v.id")
        
        # Construir filtros dinámicos
        condiciones = ["v.estado IN ('disponible', 'activo')"]
        valores = {}
        
        if 'marca' in params:
            condiciones.append("LOWER(m.nombre) LIKE :marca")
            valores['marca'] = f"%{params['marca'].lower()}%"
        if 'precio_max' in params:
            condiciones.append("v.precio <= :precio_max")
            valores['precio_max'] = params['precio_max']
        if 'anio' in params:
            condiciones.append("v.anio >= :anio_min")
            valores['anio_min'] = params['anio'] - 2
        
        where_clause = " AND ".join(condiciones)
        
        sql = f"""
            SELECT 
                v.id,
                v.slug,
                v.precio,
                v.anio,
                m.nombre AS marca,
                mo.nombre AS modelo,
                (SELECT MIN(url_imagen) FROM imagenes_vehiculos WHERE id_vehiculo = v.id) AS imagen
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE {where_clause}
            ORDER BY v.vistas DESC NULLS LAST
            LIMIT :limite
        """
        valores['limite'] = limite
        
        rows = db.session.execute(sqlalchemy.text(sql), valores).fetchall()
        
        result = []
        for row in rows:
            precio_raw = row[2]
            precio_fmt = f"{int(float(precio_raw)):,}".replace(',', '.') if precio_raw else "A consultar"
            imagen = row[6] or ''
            result.append({
                'id': row[0],
                'slug': row[1] or str(row[0]),
                'marca': row[4] or 'Vehículo',
                'modelo': row[5] or '',
                'anio': row[3] or '',
                'precio': precio_fmt,
                'imagen': imagen,
            })
        return result
    except Exception as e:
        print(f"⚠️  Error búsqueda AI: {e}")
        import traceback
        traceback.print_exc()
        return []


def obtener_resumen_inventario():
    """
    Genera un resumen del inventario actual para enriquecer el contexto de la IA.
    Por ejemplo: "Hay 42 Toyota, 25 Chevrolet, 18 Nissan disponibles."
    """
    try:
        resultado = db.session.execute(
            sqlalchemy.text("""
                SELECT m.nombre AS marca, COUNT(*) AS cantidad
                FROM vehiculos v
                JOIN marcas m ON v.id_marca = m.id
                WHERE v.estado IN ('disponible', 'activo')
                GROUP BY m.nombre
                ORDER BY cantidad DESC
                LIMIT 8
            """)
        ).fetchall()
        
        total = db.session.execute(
            sqlalchemy.text("SELECT COUNT(*) FROM vehiculos WHERE estado IN ('disponible', 'activo')")
        ).scalar() or 0
        
        if resultado:
            marcas_str = ", ".join([f"{r[0]} ({r[1]})" for r in resultado])
            return f"Inventario actual: {total} vehículos disponibles. Principales marcas: {marcas_str}."
        return f"Actualmente hay {total} vehículos disponibles en el catálogo."
    except Exception as e:
        print(f"⚠️  Error obteniendo inventario para IA: {e}")
        return ""

def obtener_rango_precios():
    """
    Obtiene el rango de precios del inventario actual.
    """
    try:
        r = db.session.execute(
            sqlalchemy.text("""
                SELECT MIN(precio) AS minimo, MAX(precio) AS maximo, AVG(precio)::bigint AS promedio
                FROM vehiculos WHERE estado IN ('disponible', 'activo') AND precio > 0
            """)
        ).fetchone()
        if r and r[0]:
            minimo = f"${int(r[0]):,}".replace(',', '.')
            maximo = f"${int(r[1]):,}".replace(',', '.')
            promedio = f"${int(r[2]):,}".replace(',', '.')
            return f"Rango de precios: desde {minimo} hasta {maximo} (promedio: {promedio})."
        return ""
    except Exception as e:
        print(f"⚠️  Error obteniendo precios para IA: {e}")
        return ""

def generar_respuesta_ai(mensaje, history=None):
    """
    Llama a GitHub Models para generar respuesta con contexto de inventario real.
    
    Args:
        mensaje: El mensaje del usuario
        history: Histórico de conversación (opcional)
    
    Returns:
        tuple: (respuesta_texto, tipo_respuesta)
    """
    if not GITHUB_TOKEN:
        return "El servicio de asistencia virtual no se encuentra configurado actualmente. Por favor, contacte con el soporte técnico.", "error"
    
    try:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 1: Construir contexto desde FAQs
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        contexto_faqs = ""
        try:
            faqs = FAQ.query.filter_by(activo=True).limit(8).all()
            if faqs:
                faq_text = [f"P: {faq.pregunta}\nR: {faq.respuesta}" for faq in faqs]
                contexto_faqs = "\n---\n".join(faq_text)
        except Exception as e:
            print(f"⚠️  Error cargando FAQs para IA: {e}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 2: Obtener resumen de inventario real
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        resumen_inventario = obtener_resumen_inventario()
        rango_precios = obtener_rango_precios()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 3: Definir prompt del sistema enriquecido
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        system_prompt = f"""Eres el Asistente Inteligente de Drive Market Colombia 🚗 — el marketplace de vehículos más avanzado de la región.

INSTRUCCIONES PRINCIPALES:
- Tu objetivo: Ayudar a usuarios a COMPRAR y VENDER vehículos en Colombia con confianza.
- Tono: Amable, profesional, comercial y proactivo. Usa emojis ocasionalmente.
- Idioma: Siempre español (Colombia).
- SOLO responde sobre vehículos, compra-venta, trámites automotrices y uso de la plataforma.
- Si el tema es ajeno, redirige amablemente.
- Incluye precios en pesos colombianos (COP) cuando corresponda.

DATOS REALES DEL INVENTARIO HOY:
{resumen_inventario}
{rango_precios}

PREGUNTAS FRECUENTES DE USUARIOS:
{contexto_faqs if contexto_faqs else "Usa tu conocimiento general sobre el proceso de compra-venta de vehículos en Colombia."}

ACCIONES QUE PUEDES SUGERIR:
- Buscar vehículos específicos por marca, modelo, precio o ciudad en /buscar
- Orientar sobre cómo publicar un anuncio gratis en /vender
- Responder dudas sobre trámites (papelería, transferencia de dominio, RUNT, etc.)
- Explicar el proceso de verificación de vendedores en Drive Market

FORMATO DE RESPUESTAS:
- Máximo 120 palabras por respuesta.
- Cuando hay vehículos disponibles de la marca que buscan, menciona el inventario real.
- Usa listas (con emojis) para pasos o instrucciones.
- Si el usuario busca un vehículo específico, además de responder, nota que el sistema buscará opciones reales para mostrarle.
"""
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 4: Preparar historial de mensajes
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        messages = [{"role": "system", "content": system_prompt}]
        
        if history and isinstance(history, list):
            messages.extend(history[-6:])  # Últimos 6 mensajes del historial
        
        messages.append({"role": "user", "content": mensaje})
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 5: Hacer llamada a GitHub Models
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GITHUB_MODEL or "gpt-4o",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 600,
            "top_p": 0.9
        }
        
        print(f"🤖 DM AI v2 — Llamando {payload['model']}...")
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 6: Procesar respuesta
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if response.status_code == 200:
            respuesta = response.json()["choices"][0]["message"]["content"]
            print(f"✅ Respuesta IA generada ({len(respuesta)} chars)")
            return respuesta, "ia"
        elif response.status_code == 401:
            print(f"❌ Error 401: Token de GitHub inválido o expirado")
            return "Error de autenticación en el servicio de inteligencia artificial. Contacte al administrador del sistema.", "error"
        elif response.status_code == 429:
            print(f"⚠️  Rate limit excedido")
            return "Se ha excedido el límite de solicitudes. Por favor, intente de nuevo en unos instantes.", "error"
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return "Se ha presentado una inconsistencia interna al procesar su consulta. ¿Podría repetirla?", "error"
            
    except requests.exceptions.Timeout:
        print("❌ Timeout en llamada a IA")
        return "El tiempo de espera para la respuesta ha expirado. Por favor, intente de nuevo.", "error"
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con servicio IA")
        return "No fue posible establecer conexión con el servicio de inteligencia artificial. Verifique su conexión de red.", "error"
    except Exception as e:
        print(f"❌ Error inesperado en generar_respuesta_ai: {e}")
        import traceback
        traceback.print_exc()
        return "Se ha producido un error inesperado en el sistema. Por favor, intente más tarde.", "error"
def generar_analisis_comparativo_ai(vehiculos):
    """
    Genera un análisis de ventas comparativo altamente persuasivo.
    """
    if not GITHUB_TOKEN:
        return "❌ IA no configurada.", "error"
    
    try:
        # Formatear datos de los vehículos para el prompt
        v_info = ""
        for i, v in enumerate(vehiculos):
            v_info += f"VEHÍCULO {i+1}:\n"
            v_info += f"- Marca/Modelo: {v.get('marca')} {v.get('modelo')}\n"
            v_info += f"- Precio: ${v.get('precio'):,.0f}\n"
            v_info += f"- Año: {v.get('anio')}\n"
            v_info += f"- Km: {v.get('kilometraje'):,.0f}\n"
            v_info += f"- Transmisión: {v.get('transmision')}\n"
            v_info += f"- Combustible: {v.get('combustible')}\n"
            v_info += f"- Motor: {v.get('cilindraje')}\n\n"

        system_prompt = """Eres el 'Cerrador Maestro' de DriveMarket Colombia. Tu misión es analizar una comparación de vehículos y persuadir al usuario de cuál es la oportunidad que no puede dejar pasar.
        
        TONO: 
        - Agresivo de ventas, sumamente seguro de ti mismo, persuasivo y lleno de energía.
        - Usa un lenguaje que genere urgencia (ej: 'oportunidad única', 'no esperes', 'invierte hoy').
        - Sé directo sobre cuál es el 'ganador' de la comparación.
        - Usa un toque de jerga colombiana elegante (ej: 'máquina', 'full equipo', 'gangazo') para conectar con el usuario local.

        ESTRUCTURA DE RESPUESTA:
        1. Resumen de Impacto: ¿Por qué estamos viendo máquinas de este nivel?
        2. El Veredicto del Experto: Dile al usuario CLARAMENTE cuál de los 2 o 3 es la mejor inversión y por qué. No seas neutral.
        3. Por qué actuar hoy: Genera la necesidad de contactar al vendedor de inmediato.

        Máximo 150 palabras. Usa negritas para resaltar puntos clave."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Compañero, analízame estos vehículos y dime cuál es el negocio de la vida:\n\n{v_info}"}
        ]

        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "model": GITHUB_MODEL,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 800
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"], "ia"
        return "El servicio de análisis de mercado no está disponible en este momento. Intente de nuevo más tarde.", "error"
        
    except Exception as e:
        print(f"❌ Error en comparativa AI: {e}")
        return "Se ha presentado un inconveniente técnico al procesar el análisis comparativo.", "error"


