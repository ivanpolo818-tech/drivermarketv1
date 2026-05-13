# soporte_routes.py - Rutas de Soporte con Asistente IA
from flask import Blueprint, render_template, request, jsonify, session
from models import db, FAQ, ConversacionChatbot, Vehiculo
from datetime import datetime
import hashlib
import time
from collections import defaultdict
from helpers.asistente_ia import (
    detectar_intencion, extraer_parametros_busqueda,
    buscar_vehiculos_ia, generar_respuesta_ai,
    get_cached_response, set_cached_response
)

soporte_bp = Blueprint('soporte', __name__)

# ── Rate Limiter en memoria (12 mensajes / 60 segundos por IP) ──
_RATE_STORE = defaultdict(list)
RATE_LIMIT   = 12   # máx. mensajes permitidos
RATE_WINDOW  = 60   # ventana en segundos

def _check_rate_limit(ip: str) -> bool:
    """Devuelve True si la petición está dentro del límite."""
    now = time.time()
    _RATE_STORE[ip] = [t for t in _RATE_STORE[ip] if now - t < RATE_WINDOW]
    if len(_RATE_STORE[ip]) >= RATE_LIMIT:
        return False
    _RATE_STORE[ip].append(now)
    return True

def generar_session_id():
    if 'chat_session_id' not in session:
        session['chat_session_id'] = hashlib.md5(str(datetime.now()).encode()).hexdigest()
    return session['chat_session_id']

@soporte_bp.route('/soporte/chat')
def chat_page():
    return render_template('soporte/chatbot.html')

@soporte_bp.route('/api/chat', methods=['POST'])
def chat_api():
    """API principal del Chat IA"""
    try:
        # ── 1. Rate Limiting ──
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        if not _check_rate_limit(ip):
            return jsonify({
                'respuesta': f'¡Un momento! Estás enviando mensajes muy rápido 😅 '
                             f'El asistente puede responder hasta {RATE_LIMIT} mensajes '
                             f'por minuto. ¿Puedes esperar unos segundos?',
                'tipo': 'rate_limit'
            }), 429

        data = request.json
        mensaje = data.get('message', '').strip()
        if not mensaje: return jsonify({'error': 'Mensaje vacío', 'respuesta': 'Por favor, escribe un mensaje.'}), 400
        
        session_id = generar_session_id()
        
        # 2. Analizar intención y parámetros
        intencion = detectar_intencion(mensaje)
        params = extraer_parametros_busqueda(mensaje)

        # 3. Obtener historial reciente para contexto conversacional
        # Prioridad: historial del cliente (sesión activa) > historial de BD
        client_history = data.get('history', [])
        history = None
        if client_history and isinstance(client_history, list):
            history = client_history[-6:]
        else:
            try:
                conversaciones_prev = ConversacionChatbot.query.filter_by(
                    session_id=session_id
                ).order_by(ConversacionChatbot.fecha_creacion.desc()).limit(4).all()
                if conversaciones_prev:
                    history = []
                    for c in reversed(conversaciones_prev):
                        history.append({"role": "user", "content": c.pregunta})
                        history.append({"role": "assistant", "content": c.respuesta})
            except Exception:
                history = None

        # 4. Cache: solo aplica para preguntas sin historial (FAQ-like)
        cache_key = None
        if not history:
            import hashlib as _hl
            cache_key = _hl.md5(mensaje.strip().lower().encode()).hexdigest()
            cached = get_cached_response(cache_key)
            if cached:
                sugerencias_cache = buscar_vehiculos_ia(params) if (intencion['intencion'] == 'comprar' or params) else []
                # Guardar log tambien para respuestas en cache (necesario para feedback)
                conv_cache = ConversacionChatbot(
                    usuario_id=session.get('usuario_id'),
                    session_id=session_id,
                    pregunta=mensaje,
                    respuesta=cached,
                    tipo_respuesta='cache'
                )
                db.session.add(conv_cache)
                db.session.commit()
                return jsonify({
                    'respuesta': cached,
                    'tipo': 'cache',
                    'intencion': intencion['intencion'],
                    'conversacion_id': conv_cache.id,
                    'sugerencias': sugerencias_cache
                })

        # 5. Obtener respuesta conversacional de la IA
        respuesta_ia, tipo = generar_respuesta_ai(mensaje, history)

        # Guardar en caché si no había historial
        if cache_key and tipo == 'ia':
            set_cached_response(cache_key, respuesta_ia)

        # 6. Buscar sugerencias reales en el inventario
        sugerencias = []
        if intencion['intencion'] == 'comprar' or params:
            sugerencias = buscar_vehiculos_ia(params)

        # 7. Guardar log
        conv = ConversacionChatbot(
            usuario_id=session.get('usuario_id'),
            session_id=session_id,
            pregunta=mensaje,
            respuesta=respuesta_ia,
            tipo_respuesta=tipo
        )
        db.session.add(conv)
        db.session.commit()

        return jsonify({
            'respuesta': respuesta_ia,
            'tipo': tipo,
            'intencion': intencion['intencion'],
            'conversacion_id': conv.id,
            'sugerencias': sugerencias
        })
        
    except Exception as e:
        print(f"Error crítico en chat_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'respuesta': "Lo siento, tuve un error interno al procesar tu solicitud. ¿Podrías intentar de nuevo o preguntarme sobre otra marca?",
            'tipo': 'error',
            'error_detail': str(e)
        })

@soporte_bp.route('/api/chat/feedback', methods=['POST'])
def chat_feedback():
    try:
        data = request.json
        conv_id = data.get('conversacion_id')
        util = data.get('util')
        conv = ConversacionChatbot.query.get(conv_id)
        if conv:
            conv.feedback = util
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'No encontrada'}), 404
    except Exception as e:
        print(f"Error en chat_feedback: {e}")
        return jsonify({'error': str(e)}), 500

@soporte_bp.route('/api/faqs', methods=['GET'])
def obtener_faqs():
    """Obtiene las FAQs activas para mostrar en el chatbot"""
    try:
        categoria = request.args.get('categoria', 'general')
        faqs = FAQ.query.filter_by(activo=True).filter_by(categoria=categoria).order_by(FAQ.orden.asc()).limit(10).all()
        
        return jsonify([{
            'id': f.id,
            'pregunta': f.pregunta,
            'respuesta': f.respuesta,
            'categoria': f.categoria,
            'orden': f.orden
        } for f in faqs])
    except Exception as e:
        print(f"Error en obtener_faqs: {e}")
        return jsonify({'error': str(e)}), 500

@soporte_bp.route('/api/chat/historial', methods=['GET'])
def obtener_historial():
    """Obtiene el historial de chat del usuario actual"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        session_id = session.get('chat_session_id')
        conversaciones = ConversacionChatbot.query.filter_by(
            usuario_id=session.get('usuario_id'),
            session_id=session_id
        ).order_by(ConversacionChatbot.fecha_creacion.desc()).limit(50).all()
        
        return jsonify([{
            'id': c.id,
            'pregunta': c.pregunta,
            'respuesta': c.respuesta,
            'tipo': c.tipo_respuesta,
            'timestamp': c.fecha_creacion.isoformat()
        } for c in conversaciones])
    except Exception as e:
        print(f"Error en obtener_historial: {e}")
        return jsonify({'error': str(e)}), 500

@soporte_bp.route('/api/chat/estado', methods=['GET'])
def obtener_estado():
    """Verifica el estado del servicio de IA"""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        github_token = os.getenv('GITHUB_TOKEN')
        github_model = os.getenv('GITHUB_MODEL', 'gpt-4o')
        
        return jsonify({
            'status': 'operational' if github_token else 'unconfigured',
            'modelo': github_model,
            'servicio': 'GitHub Models',
            'configurado': bool(github_token)
        })
    except Exception as e:
        print(f"Error en obtener_estado: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@soporte_bp.route('/admin/ia/analytics')
def ia_analytics():
    """Panel de Analytics del Chatbot IA — solo para admins."""
    from flask import abort
    if session.get('rol') not in ['admin', 'superadmin']:
        abort(403)
    return render_template('admin/ia_analytics.html')

@soporte_bp.route('/api/admin/ia/stats', methods=['GET'])
def ia_stats_api():
    """Devuelve estadísticas del chatbot para el panel admin."""
    from flask import abort
    if session.get('rol') not in ['admin', 'superadmin']:
        abort(403)
    try:
        import sqlalchemy
        # ── Total de conversaciones
        total = ConversacionChatbot.query.count()

        # ── Feedback
        positivos = ConversacionChatbot.query.filter_by(feedback=True).count()
        negativos = ConversacionChatbot.query.filter_by(feedback=False).count()
        tasa_fb   = round((positivos / (positivos + negativos) * 100), 1) if (positivos + negativos) > 0 else 0

        # ── Top 10 preguntas más frecuentes (ultimos 30 días)
        top_preguntas = db.session.execute(sqlalchemy.text("""
            SELECT pregunta, COUNT(*) as veces
            FROM conversaciones_chatbot
            WHERE fecha_creacion >= NOW() - INTERVAL '30 days'
            GROUP BY pregunta
            ORDER BY veces DESC
            LIMIT 10
        """)).fetchall()

        # ── Uso por hora del día (últimos 30 días)
        por_hora = db.session.execute(sqlalchemy.text("""
            SELECT EXTRACT(HOUR FROM fecha_creacion)::int AS hora, COUNT(*) AS total
            FROM conversaciones_chatbot
            WHERE fecha_creacion >= NOW() - INTERVAL '30 days'
            GROUP BY hora ORDER BY hora
        """)).fetchall()

        # ── Conversaciones por día (últimos 14 días)
        por_dia = db.session.execute(sqlalchemy.text("""
            SELECT DATE(fecha_creacion) AS dia, COUNT(*) AS total
            FROM conversaciones_chatbot
            WHERE fecha_creacion >= NOW() - INTERVAL '14 days'
            GROUP BY dia ORDER BY dia
        """)).fetchall()

        # ── Usuarios únicos (sesiones únicas)
        sesiones_unicas = db.session.execute(sqlalchemy.text(
            "SELECT COUNT(DISTINCT session_id) FROM conversaciones_chatbot"
        )).scalar() or 0

        # ── % servido desde caché (tipo = 'cache')
        desde_cache = ConversacionChatbot.query.filter_by(tipo_respuesta='cache').count()
        cache_pct = round((desde_cache / total * 100), 1) if total > 0 else 0

        return jsonify({
            'total': total,
            'sesiones_unicas': sesiones_unicas,
            'feedback': {'positivos': positivos, 'negativos': negativos, 'tasa': tasa_fb},
            'cache_pct': cache_pct,
            'top_preguntas': [{'pregunta': r[0][:80], 'veces': r[1]} for r in top_preguntas],
            'por_hora': [{'hora': r[0], 'total': r[1]} for r in por_hora],
            'por_dia': [{'dia': str(r[0]), 'total': r[1]} for r in por_dia],
        })
    except Exception as e:
        print(f"Error en ia_stats_api: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

print("✅ Soporte routes cargadas correctamente")
print("  - POSt /api/chat (chat principal)")
print("  - POST /api/chat/feedback (feedback)")
print("  - GET /api/faqs (obtener FAQs)")
print("  - GET /api/chat/historial (historial de chat)")
print("  - GET /api/chat/estado (estado del servicio)")

@soporte_bp.route('/api/docs/chat', methods=['POST', 'OPTIONS'])
def chat_docs_api():
    """Endpoint API para el Chatbot de MkDocs (Documentacion Tecnica)"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    data = request.get_json()
    if not data or not data.get('mensaje'):
        return jsonify({'error': 'Mensaje vacio'}), 400
        
    mensaje = data.get('mensaje')
    history = data.get('history', [])
    
    from helpers.docs_ai import generar_respuesta_docs_ai
    respuesta, tipo = generar_respuesta_docs_ai(mensaje, history)
    
    return jsonify({
        'respuesta': respuesta,
        'tipo': tipo
    })
    

