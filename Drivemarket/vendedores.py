import traceback
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app, jsonify
from db_config import conexion
import psycopg2
import psycopg2.extras
import json
import os
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests

from helpers.image_utils import apply_watermark
from helpers.vendedor_utils import get_market_average, toggle_featured

vendedor_bp = Blueprint('vendedor', __name__, url_prefix='/vendedor')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def login_requerido_vendedor(f):
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Se requiere iniciar sesión para acceder a las funciones administrativas de vendedor.", "warning")
            return redirect(url_for('login'))
        if session.get('rol') not in ['vendedor', 'admin', 'superadmin', 'moderador', 'editor']:
            flash("Acceso restringido. Esta sección está reservada para cuentas con perfil de vendedor autorizado.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@vendedor_bp.context_processor
def inject_sidebar_stats():
    # Inject seller stats globally into all templates rendered by this blueprint
    stats = {
        'total_vehiculos': 0,
        'rating_promedio': '5.0',
        'tasa_respuesta': '100'
    }
    if 'usuario_id' in session and session.get('rol') in ['vendedor', 'admin', 'superadmin']:
        uid = session['usuario_id']
        try:
            cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT COUNT(*) as num FROM vehiculos WHERE id_usuario = %s AND estado = 'activo'", (uid,))
            res = cursor.fetchone()
            if res:
                stats['total_vehiculos'] = res['num']
            # Rating and Tasa de Respuesta are defaulted for now.
            # You can update this later when those tables exist.
            cursor.close()
        except Exception as e:
            conexion.rollback()
    
    return stats


def _get_vendedor_base(uid):
    """
    Funcion para automatizar la obtencion de informacion comun para el vendedor.
    """
    try:
        # Migracion rapida para Premium Features (solo corre una vez si faltan columnas)
        # Esto es util si no puedo correr scripts externos de migracion.
        cursor = conexion.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'vehiculos' AND column_name = 'es_destacado'")
        if not cursor.fetchone():
            print("🚀 Agregando columnas Premium a 'vehiculos'...")
            cursor.execute("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS es_destacado BOOLEAN DEFAULT FALSE")
            cursor.execute("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS fecha_destacado TIMESTAMP")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehiculo_destacado ON vehiculos (es_destacado)")
            conexion.commit()
            
        # 2. Migracion para Notificaciones (si falta la tabla)
        cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'notificaciones'")
        if not cursor.fetchone():
            print("🚀 Creando tabla 'notificaciones'...")
            cursor.execute("""
                CREATE TABLE notificaciones (
                    id SERIAL PRIMARY KEY,
                    id_usuario INTEGER REFERENCES usuarios(id),
                    tipo VARCHAR(50),
                    titulo VARCHAR(255),
                    mensaje TEXT,
                    leida BOOLEAN DEFAULT FALSE,
                    fecha_creacion TIMESTAMP DEFAULT NOW(),
                    fecha_leida TIMESTAMP,
                    url_accion VARCHAR(255),
                    id_relacion INTEGER
                )
            """)
            conexion.commit()
            
        # 3. Migración para Favoritos (asegurar fecha_creacion para analítica)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'favoritos' AND column_name = 'fecha_creacion'")
        if not cursor.fetchone():
            print("🚀 Agregando 'fecha_creacion' a la tabla 'favoritos'...")
            cursor.execute("ALTER TABLE favoritos ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW()")
            conexion.commit()
        
        # 4. Migración para tabla de eventos de vehículos (WhatsApp clicks, etc.)
        cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'vehiculo_eventos'")
        if not cursor.fetchone():
            print("🚀 Creando tabla 'vehiculo_eventos'...")
            cursor.execute("""
                CREATE TABLE vehiculo_eventos (
                    id SERIAL PRIMARY KEY,
                    id_vehiculo INTEGER REFERENCES vehiculos(id) ON DELETE CASCADE,
                    id_usuario INTEGER REFERENCES usuarios(id),
                    tipo VARCHAR(50) NOT NULL DEFAULT 'whatsapp_click',
                    fecha TIMESTAMP DEFAULT NOW(),
                    ip VARCHAR(45),
                    user_agent TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_vehiculo ON vehiculo_eventos (id_vehiculo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON vehiculo_eventos (tipo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON vehiculo_eventos (fecha)")
            conexion.commit()
            print("✅ Tabla 'vehiculo_eventos' creada exitosamente.")
            
        # 5. Migración para Anuncios Destacados Manuales en `vehiculos`
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'vehiculos' AND column_name = 'plan_destacado'")
        if not cursor.fetchone():
            print("🚀 Agregando columnas de Anuncios Destacados Manuales a la tabla 'vehiculos'...")
            cursor.execute("""
                ALTER TABLE vehiculos 
                ADD COLUMN IF NOT EXISTS plan_destacado BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS comprobante_pago VARCHAR(255),
                ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'ninguno',
                ADD COLUMN IF NOT EXISTS fecha_fin_destacado TIMESTAMP
            """)
            conexion.commit()
            print("✅ Columnas de monetización añadidas.")
            
        # 6. Migración para borrado de conversaciones (Vendedor/Comprador)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'conversaciones' AND column_name = 'eliminada_vendedor'")
        if not cursor.fetchone():
            print("🚀 Agregando columnas de borrado a 'conversaciones'...")
            cursor.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS eliminada_vendedor BOOLEAN DEFAULT FALSE")
            cursor.execute("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS eliminada_comprador BOOLEAN DEFAULT FALSE")
            conexion.commit()
            print("✅ Columnas de borrado añadidas.")
            
        cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'preferencias_usuario'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE preferencias_usuario (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                    meta_ingresos NUMERIC(15, 2) DEFAULT 0,
                    meta_ventas INTEGER DEFAULT 0,
                    meta_clientes INTEGER DEFAULT 0
                )
            """)
            conexion.commit()
        else:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'preferencias_usuario' AND column_name = 'meta_ingresos'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE preferencias_usuario ADD COLUMN IF NOT EXISTS meta_ingresos NUMERIC(15,2) DEFAULT 0, ADD COLUMN IF NOT EXISTS meta_ventas INTEGER DEFAULT 0, ADD COLUMN IF NOT EXISTS meta_clientes INTEGER DEFAULT 0")
                conexion.commit()
            
        cursor.close()
    except Exception as e:
        print(f"Error en auto-migracion: {e}")
        conexion.rollback()

    """
    Retorna el diccionario con la info base del vendedor, sus metas y estado de verificación.
    """
    vendedor = None
    estado_verificacion = 'pendiente'
    meta_ventas = 0
    meta_clientes = 0
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Información base del usuario
        cursor.execute("SELECT id, nombre, username, email, foto, rol FROM usuarios WHERE id = %s", (uid,))
        vendedor = cursor.fetchone()
        
        if vendedor:
            # Estado verificación y descripción del vendedor
            cursor.execute("SELECT * FROM perfil_vendedor WHERE usuario_id = %s", (uid,))
            perfil = cursor.fetchone()
            if perfil:
                estado_verificacion = perfil.get('estado_verificacion', 'pendiente')
                vendedor['perfil_vend'] = perfil
            else:
                vendedor['perfil_vend'] = {}
                
            # Preferencias para metas
            cursor.execute("SELECT meta_ingresos, meta_ventas, meta_clientes FROM preferencias_usuario WHERE usuario_id = %s", (uid,))
            prefs = cursor.fetchone()
            if prefs:
                meta_ventas = prefs.get('meta_ventas') or 0
                meta_clientes = prefs.get('meta_clientes') or 0
                
        cursor.close()
    except Exception as e:
        print(f"Error consultando base del vendedor: {e}")
        conexion.rollback()
        
    return vendedor, meta_ventas, meta_clientes, estado_verificacion, vendedor.get('perfil_vend') if vendedor else {}

@vendedor_bp.route('/generar_descripcion', methods=['POST'])
@login_requerido_vendedor
def generar_descripcion_ia():
    """
    Utiliza GitHub Models para generar una descripción profesional del vehículo.
    """
    data = request.json
    if not data:
        return jsonify({'ok': False, 'msg': 'No se enviaron datos.'}), 400

    marca = data.get('marca', 'Vehículo')
    modelo = data.get('modelo', 'Premium')
    anio = data.get('anio', '')
    kilometraje = data.get('kilometraje', '')
    version = data.get('version', '')
    extras = data.get('extras', [])
    ciudad = data.get('ciudad', '')

    # Obtener token de entorno
    github_token = os.getenv('GITHUB_TOKEN')
    github_model = os.getenv('GITHUB_MODEL', 'gpt-4o')

    if not github_token:
        return jsonify({'ok': False, 'msg': 'Servicio de IA no configurado (Token faltante).'}), 500

    # Construir el prompt
    prompt = f"""
    Actúa como un experto en ventas de vehículos de lujo y automóviles premium. 
    Crea una descripción profesional, persuasiva y optimizada para la venta del siguiente vehículo:
    - Marca y Modelo: {marca} {modelo} {anio}
    - Versión: {version}
    - Kilometraje: {kilometraje} km
    - Ubicación: {ciudad}
    - Características/Extras: {', '.join(extras) if extras else 'Full equipo'}

    La descripción debe:
    1. Tener un tono elegante pero directo.
    2. Resaltar la exclusividad, confiabilidad y el excelente estado del vehículo.
    3. Estar organizada en párrafos cortos o puntos clave.
    4. Incluir emojis profesionales relacionados con el mundo automotriz.
    5. Finalizar con un llamado a la acción invitando a contactar para agendar una cita o prueba de manejo.
    
    RESPONDE SOLO CON EL TEXTO DE LA DESCRIPCIÓN EN ESPAÑOL.
    """

    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": github_model,
        "messages": [
            {"role": "system", "content": "Eres un asistente experto en redacción publicitaria para el sector automotriz premium."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_data = response.json()
            descripcion = res_data["choices"][0]["message"]["content"].strip()
            return jsonify({'ok': True, 'descripcion': descripcion})
        else:
            print(f"Error AI status: {response.status_code} - {response.text}")
            return jsonify({'ok': False, 'msg': f'Error de servidor IA ({response.status_code})'}), 500
    except Exception as e:
        print(f"Error AI Exception: {e}")
        return jsonify({'ok': False, 'msg': f'Error de conexión con la IA: {str(e)}'}), 500

def _get_vendedor_activity(uid):
    """Auxiliar para obtener el feed de actividad consolidado."""
    actividad_reciente = []
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # A. Favoritos
        cursor.execute("""
            SELECT f.id, f.fecha_creacion as fecha, m.nombre as marca, mo.nombre as modelo, 'favorito' as tipo
            FROM favoritos f
            JOIN vehiculos v ON f.id_vehiculo = v.id
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY f.fecha_creacion DESC LIMIT 5
        """, (uid,))
        for row in cursor.fetchall():
            actividad_reciente.append({
                'fecha': row['fecha'],
                'icono': 'fas fa-heart',
                'color': '#EF4444',
                'color_bg': 'rgba(239, 68, 68, 0.1)',
                'titulo': 'Favorito agregado',
                'detalle': f"{row['marca']} {row['modelo']} fue guardado",
                'fecha_texto': row['fecha'].strftime('%d/%m/%Y %H:%M') if row['fecha'] else 'Recientemente'
            })

        # B. Mensajes Nuevos
        cursor.execute("""
            SELECT m.id, m.fecha_envio as fecha, m.contenido as mensaje, u.nombre as remitente, 'mensaje' as tipo
            FROM mensajes m
            JOIN conversaciones c ON m.id_conversacion = c.id
            JOIN usuarios u ON m.id_remitente = u.id
            WHERE c.id_vendedor = %s AND m.id_remitente != %s
            ORDER BY m.fecha_envio DESC LIMIT 5
        """, (uid, uid))
        for row in cursor.fetchall():
            actividad_reciente.append({
                'fecha': row['fecha'],
                'icono': 'fas fa-comment-dots',
                'color': '#3B82F6',
                'color_bg': 'rgba(59, 130, 246, 0.1)',
                'titulo': f"Nuevo mensaje",
                'detalle': f"{row['remitente']}: \"{row['mensaje'][:25]}...\"",
                'fecha_texto': row['fecha'].strftime('%d/%m/%Y %H:%M') if row['fecha'] else 'Recientemente'
            })

        # C. Publicaciones
        cursor.execute("""
            SELECT v.id, v.fecha_publicacion as fecha, m.nombre as marca, mo.nombre as modelo, 'publicacion' as tipo
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY fecha_publicacion DESC LIMIT 3
        """, (uid,))
        for row in cursor.fetchall():
            actividad_reciente.append({
                'fecha': row['fecha'],
                'icono': 'fas fa-plus-circle',
                'color': '#FF6A00',
                'color_bg': 'rgba(255, 106, 0, 0.1)',
                'titulo': 'Vehículo publicado',
                'detalle': f"Has subido un {row['marca']} {row['modelo']}",
                'fecha_texto': row['fecha'].strftime('%d/%m/%Y %H:%M') if row['fecha'] else 'Recientemente'
            })
        # Ordenar por fecha manejando posibles valores nulos (las nulas al final)
        actividad_reciente.sort(key=lambda x: x['fecha'] if x['fecha'] else datetime.min, reverse=True)
        return actividad_reciente[:10]
    except Exception as e:
        print(f"Error en feed de actividad: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()


@vendedor_bp.route('/dashboard')
@login_requerido_vendedor
def dashboard():
    uid = session['usuario_id']
    vendedor, meta_ventas, meta_clientes, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    # Valores por defecto para el UI si fallan consultas
    vehiculos_activos = 0
    vehiculos_mes = 0
    vistas_mes = 0
    favoritos_total = 0
    mensajes_no_leidos = 0
    ganancias_mes = 0
    potencial_ganancia = 0
    
    vendidos_mes = 0
    pct_ventas = 0
    clientes_mes = 0
    pct_clientes = 0
    
    meses_labels = []
    vistas_data = []
    favoritos_data = []
    
    dias_labels = []
    vistas_dia_data = []
    
    ingresos_labels = []
    ingresos_data = []
    
    ultimos_vehiculos = []
    perfil_completo = 0
    vistas_mes = 0 # Inicializado aquí también para seguridad
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Total vehículos activos
        cursor.execute("SELECT COUNT(*) AS c FROM vehiculos WHERE id_usuario = %s AND (estado IS NULL OR estado NOT IN ('vendido','pausado'))", (uid,))
        vehiculos_activos = (cursor.fetchone() or {}).get('c', 0)
        
        # 2. Vehículos publicados en el mes actual
        cursor.execute("""
            SELECT COUNT(*) AS c FROM vehiculos 
            WHERE id_usuario = %s 
              AND EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (uid,))
        vehiculos_mes = (cursor.fetchone() or {}).get('c', 0)
        
        # 2.5 Vistas totales (de todos los vehículos activos)
        cursor.execute("""
            SELECT SUM(vistas) AS v FROM vehiculos 
            WHERE id_usuario = %s AND (estado IS NULL OR estado != 'eliminado')
        """, (uid,))
        vistas_mes = (cursor.fetchone() or {}).get('v', 0) or 0
        
        # 3. Vehículos VENDIDOS este mes y % de meta
        cursor.execute("""
            SELECT COUNT(*) AS c FROM vehiculos 
            WHERE id_usuario = %s AND estado = 'vendido'
              AND EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (uid,))
        vendidos_mes = (cursor.fetchone() or {}).get('c', 0)
        pct_ventas = min(100, int((vendidos_mes / meta_ventas) * 100)) if meta_ventas > 0 else 0
        
        # 4. Potencial Ganancia (suma de vehículos activos)
        cursor.execute("""
            SELECT SUM(precio) AS total FROM vehiculos 
            WHERE id_usuario = %s AND (estado IS NULL OR estado NOT IN ('vendido','pausado'))
        """, (uid,))
        res = cursor.fetchone()
        if res and res.get('total'):
            potencial_ganancia = res['total']
            
        # 5. Ganancia generada este mes (suma de vehículos vendidos este mes)
        cursor.execute("""
            SELECT SUM(precio) AS total FROM vehiculos 
            WHERE id_usuario = %s AND estado = 'vendido'
              AND EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (uid,))
        res = cursor.fetchone()
        if res and res.get('total'):
            ganancias_mes = res['total']
            
        # 6. Favoritos totales a los vehículos
        cursor.execute("""
            SELECT COUNT(*) AS c FROM favoritos f
            JOIN vehiculos v ON f.id_vehiculo = v.id
            WHERE v.id_usuario = %s
        """, (uid,))
        favoritos_total = (cursor.fetchone() or {}).get('c', 0)
        
        # 7. Clientes contactando y sus metas
        cursor.execute("""
             SELECT COUNT(DISTINCT id_remitente) AS c FROM mensajes m
             JOIN conversaciones c ON m.id_conversacion = c.id
             WHERE c.id_vendedor = %s
               AND m.id_remitente != %s
               AND EXTRACT(MONTH FROM m.fecha_envio) = EXTRACT(MONTH FROM CURRENT_DATE)
               AND EXTRACT(YEAR FROM m.fecha_envio) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (uid, uid))
        clientes_mes = (cursor.fetchone() or {}).get('c', 0)
        pct_clientes = min(100, int((clientes_mes / meta_clientes) * 100)) if meta_clientes > 0 else 0
        
        # 7.2 Tracking de WhatsApp (Conversión Real)
        cursor.execute("""
            SELECT COUNT(*) AS c FROM vehiculo_eventos e
            JOIN vehiculos v ON e.id_vehiculo = v.id
            WHERE v.id_usuario = %s AND e.tipo = 'whatsapp_click'
        """, (uid,))
        total_whatsapp = (cursor.fetchone() or {}).get('c', 0)

        # 7.5 Mensajes NO LEÍDOS (total para la campana/bubble)
        cursor.execute("""
            SELECT COUNT(*) AS c FROM mensajes m
            JOIN conversaciones c ON m.id_conversacion = c.id
            WHERE (c.id_vendedor = %s OR c.id_comprador = %s)
              AND m.id_remitente != %s AND m.leido = false
        """, (uid, uid, uid))
        mensajes_no_leidos = (cursor.fetchone() or {}).get('c', 0)
        
        # 8. Gráficas de Actividad Mensual (Vistas)
        cursor.execute("""
            SELECT TO_CHAR(v.fecha_publicacion, 'YYYY-MM') AS mes, COALESCE(SUM(v.vistas), 0) AS total_vistas
            FROM vehiculos v
            WHERE v.id_usuario = %s
              AND v.fecha_publicacion >= CURRENT_DATE - INTERVAL '12 MONTH'
            GROUP BY mes ORDER BY mes ASC
        """, (uid,))
        for row in cursor.fetchall():
            meses_labels.append(row['mes'])
            vistas_data.append(row['total_vistas'])
            favoritos_data.append(0) # Filler
            
        # 9. Últimos vehículos para la tabla del dashboard (Ajustado con LEFT JOIN y estado)
        cursor.execute("""
            SELECT v.id, v.precio, v.anio, v.vistas, v.fecha_publicacion, v.estado, v.plan_destacado, v.estado_pago,
                   m.nombre AS marca, mo.nombre AS modelo,
                   COALESCE(
                       (SELECT url_imagen FROM imagenes_vehiculos iv WHERE iv.id_vehiculo = v.id ORDER BY iv.id ASC LIMIT 1),
                       'img/default_car.jpg'
                   ) AS imagen
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY v.id DESC LIMIT 5
        """, (uid,))
        ultimos_vehiculos = cursor.fetchall()
            
        # 10. Vistas por Día (Últimos 30 días)
        cursor.execute("""
            SELECT CAST(fecha_publicacion AS DATE) AS dia, COALESCE(SUM(vistas),0) AS total
            FROM vehiculos
            WHERE id_usuario = %s AND fecha_publicacion >= CURRENT_DATE - INTERVAL '30 DAY'
            GROUP BY dia ORDER BY dia ASC
        """, (uid,))
        for row in cursor.fetchall():
            dias_labels.append(str(row['dia']))
            vistas_dia_data.append(row['total'])

        # 10. Ingresos por mes (Facturación)
        cursor.execute("""
            SELECT TO_CHAR(fecha_publicacion, 'YYYY-MM') AS mes, SUM(precio) AS total
            FROM vehiculos
            WHERE id_usuario = %s AND estado = 'vendido'
              AND fecha_publicacion >= CURRENT_DATE - INTERVAL '6 MONTH'
            GROUP BY mes ORDER BY mes ASC
        """, (uid,))
        for row in cursor.fetchall():
            ingresos_labels.append(row['mes'])
            ingresos_data.append(row['total'])
            
    except Exception as e:
        print(f"Error en dashboard vendedor: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
    finally:
        try:
            cursor.close()
        except:
            pass

    # Fallback: meses recientes con ceros para evitar gráficos vacíos
    if not meses_labels:
        today = datetime.today()
        for i in range(5, -1, -1):
            label = (today - timedelta(days=30*i)).strftime('%b %y')
            meses_labels.append(label)
            vistas_data.append(0)
            favoritos_data.append(0)

    datos_mensuales = {
        'labels': meses_labels,
        'vistas': vistas_data,
        'favoritos': favoritos_data
    }
    
    vistas_por_dia = []
    for i in range(len(dias_labels)):
        vistas_por_dia.append({'dia': dias_labels[i], 'total': vistas_dia_data[i]})

    ingresos_por_mes = []
    for i in range(len(ingresos_labels)):
        ingresos_por_mes.append({'mes': ingresos_labels[i], 'total': ingresos_data[i]})
        
    # Calcular completitud del perfil (básico)
    checklist = [vendedor.get('foto'), vendedor.get('nombre'), vendedor.get('email')] if vendedor else []
    if perfil_vend:
        checklist.extend([perfil_vend.get('descripcion'), perfil_vend.get('direccion_negocio')])
    if checklist:
        perfil_completo = int((len([f for f in checklist if f]) / len(checklist)) * 100)

    metas = {
        'ventas': {'actual': vendidos_mes, 'meta': meta_ventas, 'pct': pct_ventas},
        'clientes': {'actual': clientes_mes, 'meta': meta_clientes, 'pct': pct_clientes},
        'respuesta': {'actual': 100, 'meta': 100, 'pct': 100},
        'rating': {'actual': 5.0, 'meta': 5.0, 'pct': 100}
    }

    # Obtener Market Insights (análisis de mercado)
    market_insight = _get_market_insight(uid)

    # 11. Obtener Notificaciones (Reales)
    notificaciones_reales = []
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notificaciones WHERE id_usuario = %s AND leida = FALSE ORDER BY fecha_creacion DESC LIMIT 5", (uid,))
        notificaciones_reales = cursor.fetchall()
        cursor.close()
    except:
        pass

    # 12. Actividad Reciente Consolidada
    actividad_reciente = _get_vendedor_activity(uid)

    return render_template('vendedor/dashboard.html', 
        vendedor=vendedor,
        perfil_vend=perfil_vend,
        total_vehiculos=vehiculos_activos,
        vehiculos_mes=vehiculos_mes,
        total_favoritos=favoritos_total,
        total_whatsapp=total_whatsapp,
        mensajes_no_leidos=mensajes_no_leidos,
        potencial_ganancia=potencial_ganancia,
        ganancias_mes=ganancias_mes,
        datos_mensuales_json=json.dumps(datos_mensuales),
        vistas_por_dia=vistas_por_dia,
        ingresos_por_mes=ingresos_por_mes,
        ultimos_vehiculos=ultimos_vehiculos,
        perfil_completo=perfil_completo,
        vistas_mes=vistas_mes,
        metas=metas,
        market_insight=market_insight,
        notificaciones=notificaciones_reales,
        actividad_reciente=actividad_reciente,
        estado_verificacion=estado_verificacion
    )

@vendedor_bp.route('/api/stats/activity')
@login_requerido_vendedor
def api_stats_activity():
    uid = session['usuario_id']
    actividades = _get_vendedor_activity(uid)
    # Convertir fechas a string para JSON
    for act in actividades:
        if 'fecha' in act:
            del act['fecha'] # No es necesario en el JSON final ya tenemos fecha_texto
    return jsonify(actividades)

@vendedor_bp.route('/api/stats/chart')
@login_requerido_vendedor
def api_stats_chart():
    uid = session['usuario_id']
    period = request.args.get('period', 'month') # day, week, month
    metric = request.args.get('metric', 'vistas') # vistas, publicaciones
    
    labels = []
    values = []
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Definir la subconsulta según la métrica
        if metric == 'vistas':
            subquery = "SELECT vistas as val, CAST(fecha_publicacion AS DATE) as dt FROM vehiculos WHERE id_usuario = %s"
            agg_func = "SUM(sub.val)"
        elif metric == 'publicaciones':
            subquery = "SELECT 1 as val, CAST(fecha_publicacion AS DATE) as dt FROM vehiculos WHERE id_usuario = %s"
            agg_func = "COUNT(sub.val)"
        else: # favoritos
            subquery = """
                SELECT 1 as val, CAST(f.fecha_creacion AS DATE) as dt 
                FROM favoritos f 
                JOIN vehiculos v ON f.id_vehiculo = v.id 
                WHERE v.id_usuario = %s
            """
            agg_func = "COUNT(sub.val)"

        # 2. Ejecutar según el periodo
        if period == 'day':
            query = f"""
                SELECT days.d::date as label, COALESCE({agg_func}, 0) as value
                FROM generate_series(CURRENT_DATE - INTERVAL '13 days', CURRENT_DATE, '1 day') AS days(d)
                LEFT JOIN ({subquery}) sub ON sub.dt = days.d::date
                GROUP BY label ORDER BY label ASC
            """
        elif period == 'week':
            query = f"""
                SELECT DATE_TRUNC('week', weeks.w)::date as label, COALESCE({agg_func}, 0) as value
                FROM generate_series(CURRENT_DATE - INTERVAL '9 weeks', CURRENT_DATE, '1 week') AS weeks(w)
                LEFT JOIN ({subquery}) sub ON DATE_TRUNC('week', sub.dt) = DATE_TRUNC('week', weeks.w)
                GROUP BY label ORDER BY label ASC
            """
        else: # month
            query = f"""
                SELECT TO_CHAR(months.m, 'YYYY-MM') as label, COALESCE({agg_func}, 0) as value
                FROM generate_series(CURRENT_DATE - INTERVAL '11 months', CURRENT_DATE, '1 month') AS months(m)
                LEFT JOIN ({subquery}) sub ON TO_CHAR(sub.dt, 'YYYY-MM') = TO_CHAR(months.m, 'YYYY-MM')
                GROUP BY label ORDER BY label ASC
            """
            
        cursor.execute(query, (uid,))
        res = cursor.fetchall()
        for row in res:
            labels.append(str(row['label']))
            values.append(int(row['value']))
            
        cursor.close()
    except Exception as e:
        print(f"Error API Chart: {e}")
        labels = ["Error"]
        values = [0]

    return jsonify({
        'labels': labels,
        'values': values,
        'metric': metric,
        'period': period
    })

@vendedor_bp.route('/api/stats/distribution')
@login_requerido_vendedor
def api_stats_distribution():
    uid = session['usuario_id']
    data = {'labels': [], 'values': [], 'colors': []}
    
    color_map = {
        'activo': '#FF6A00',
        'vendido': '#10B981',
        'pausado': '#F59E0B',
        'pendiente': '#3B82F6',
        'rechazado': '#EF4444'
    }

    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT COALESCE(estado, 'activo') as status, COUNT(*) as count 
            FROM vehiculos WHERE id_usuario = %s 
            GROUP BY status
        """, (uid,))
        
        for row in cursor.fetchall():
            s = row['status'].lower()
            data['labels'].append(s.capitalize())
            data['values'].append(row['count'])
            data['colors'].append(color_map.get(s, '#9CA3AF'))
            
        cursor.close()
    except:
        pass
        
    return jsonify(data)

@vendedor_bp.route('/api/market-insight', methods=['GET'])
@login_requerido_vendedor
def api_market_insight():
    vid = request.args.get('vid')
    if not vid:
        return jsonify({'ok': False, 'msg': 'Falta el ID del vehículo'})
    
    uid = session['usuario_id']
    insight = _get_market_insight(uid, vid=vid)
    if not insight:
        return jsonify({'ok': False, 'msg': 'No se pudo generar el análisis'})
    
    return jsonify({'ok': True, 'data': insight})

@vendedor_bp.route('/api/sync-price', methods=['POST'])
@login_requerido_vendedor
def api_sync_price():
    data = request.get_json()
    if not data:
        return jsonify({'ok': False, 'msg': 'Datos inválidos'})
    
    vid = data.get('vid')
    nuevo_precio = data.get('precio')
    
    if not vid or not nuevo_precio:
        return jsonify({'ok': False, 'msg': 'Faltan parámetros'})
        
    try:
        nuevo_precio = float(nuevo_precio)
        uid = session['usuario_id']
        
        cursor = conexion.cursor()
        cursor.execute("UPDATE vehiculos SET precio = %s WHERE id = %s AND id_usuario = %s", (nuevo_precio, vid, uid))
        if cursor.rowcount == 0:
            return jsonify({'ok': False, 'msg': 'Vehículo no encontrado o no tienes permiso'})
            
        conexion.commit()
        cursor.close()
        return jsonify({'ok': True, 'msg': 'Precio actualizado exitosamente'})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)})
def _get_market_insight(uid, vid=None):
    """Obtiene un análisis de mercado para el mejor vehículo del vendedor o uno específico."""
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if vid:
            cursor.execute("""
                SELECT v.id, v.id_marca, v.id_modelo, v.anio, v.precio, v.vistas, v.es_destacado,
                       m.nombre AS marca_nombre, mo.nombre AS modelo_nombre
                FROM vehiculos v
                LEFT JOIN marcas m ON v.id_marca = m.id
                LEFT JOIN modelos mo ON v.id_modelo = mo.id
                WHERE v.id_usuario = %s AND v.id = %s
            """, (uid, vid))
        else:
            cursor.execute("""
                SELECT v.id, v.id_marca, v.id_modelo, v.anio, v.precio, v.vistas, v.es_destacado,
                       m.nombre AS marca_nombre, mo.nombre AS modelo_nombre
                FROM vehiculos v
                LEFT JOIN marcas m ON v.id_marca = m.id
                LEFT JOIN modelos mo ON v.id_modelo = mo.id
                WHERE v.id_usuario = %s AND v.estado = 'activo'
                ORDER BY v.es_destacado DESC, v.vistas DESC NULLS LAST LIMIT 1
            """, (uid,))

        mejor_vehiculo = cursor.fetchone()
        
        if mejor_vehiculo:
            from helpers.vendedor_utils import get_market_average
            market = get_market_average(mejor_vehiculo['id_marca'], mejor_vehiculo['id_modelo'], mejor_vehiculo['anio'], mejor_vehiculo['id'])
            
            actual = float(mejor_vehiculo['precio'])
            v_name = f"{mejor_vehiculo['marca_nombre']} {mejor_vehiculo['modelo_nombre']}"

            if market:
                # Cálculos base
                avg = float(market['promedio'])
                diff_pct = ((actual - avg) / avg) * 100

                # Calculo de probabilidad dinámica
                prob = 0
                msg = ""
                if diff_pct <= -15:
                    prob = 80
                    msg = "¡Precio imbatible! Tienes un <strong>80% más</strong> de probabilidad de venta inmediata."
                elif diff_pct <= -5:
                    prob = 40
                    msg = "Tu vehículo está a un <strong>precio excelente</strong>. Tienes un 40% más de probabilidad de venta."
                elif diff_pct <= 5:
                    prob = 20
                    msg = "Precio justo y <strong>competitivo</strong>. Tienes un 20% más de probabilidad de venta."
                else:
                    prob = -30
                    msg = "Estás por encima del mercado. Considera <strong>ajustar tu precio</strong> para mejorar la rotación."

                return {
                    'id': v_name,
                    'id_vehiculo': mejor_vehiculo['id'],
                    'precio_actual': actual,
                    'precio_mercado': avg,
                    'diferencia': round(diff_pct, 1),
                    'muestra': market['muestra'],
                    'oportunidad': diff_pct < 0,
                    'competitivo': actual <= (avg * 1.05),
                    'msg': msg,
                    'prob_extra': prob
                }
            else:
                # Caso: Único vehículo en el sistema (sin muestra)
                return {
                    'id': v_name,
                    'id_vehiculo': mejor_vehiculo['id'],
                    'precio_actual': actual,
                    'precio_mercado': 0, 'diferencia': 0,
                    'muestra': 0, 'oportunidad': False, 'competitivo': True, 'msg': 'Único en el mercado'
                }
        
        # Fallback if no vehicle
        return {
            'id': "Analizando flota...",
            'precio_actual': 0, 'precio_mercado': 0, 'diferencia': 0,
            'muestra': 0, 'oportunidad': False, 'competitivo': True, 'demo': True
        }
    except Exception as e:
        print(f"Error en inteligencia de mercado: {e}")
        return None

@vendedor_bp.route('/vehiculo/<int:vid>/actualizar-precio', methods=['POST'])
@login_requerido_vendedor
def actualizar_precio(vid):
    """Actualiza el precio de un vehículo de forma rápida (vía AJAX)."""
    uid = session['usuario_id']
    try:
        nuevo_precio = request.form.get('precio')
        if not nuevo_precio:
            return jsonify({'success': False, 'error': 'Falta el precio'}), 400
            
        cursor = conexion.cursor()
        # Verificar propiedad
        cursor.execute("SELECT id FROM vehiculos WHERE id = %s AND id_usuario = %s", (vid, uid))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
            
        # Actualizar
        cursor.execute("UPDATE vehiculos SET precio = %s WHERE id = %s", (nuevo_precio, vid))
        conexion.commit()
        cursor.close()
        return jsonify({'success': True, 'msg': 'Precio actualizado con éxito'})
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@vendedor_bp.route('/vehiculo/<int:vid>/toggle-destacado', methods=['POST'])
@login_requerido_vendedor
def toggle_destacado(vid):
    """
    Alterna el estado 'destacado' del vehículo (AJAX).
    """
    uid = session['usuario_id']
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT es_destacado, estado FROM vehiculos WHERE id = %s AND id_usuario = %s", (vid, uid))
        vehiculo = cursor.fetchone()
        
        if not vehiculo:
            return json.dumps({'ok': False, 'msg': 'Vehículo no encontrado'}), 404
            
        nuevo_estado = not vehiculo.get('es_destacado', False)
        
        from helpers.vendedor_utils import toggle_featured
        if toggle_featured(vid, nuevo_estado):
            return json.dumps({'ok': True, 'destacado': nuevo_estado})
        else:
            return json.dumps({'ok': False, 'msg': 'Error al actualizar estado'}), 500
    except Exception as e:
        print(f"Error toggle-destacado: {e}")
        return json.dumps({'ok': False, 'msg': str(e)}), 500
    finally:
        try: cursor.close()
        except: pass

# ---------------------------------------------------------
# API PÚBLICA: REGISTRO DE EVENTOS DE VEHÍCULO
# ---------------------------------------------------------

@vendedor_bp.route('/api/whatsapp-click', methods=['POST'])
def registrar_whatsapp_click():
    """Registra un click en el botón de WhatsApp de un vehículo."""
    try:
        data = request.get_json(silent=True) or {}
        id_vehiculo = data.get('id_vehiculo')
        if not id_vehiculo:
            return jsonify({'ok': False, 'msg': 'Falta id_vehiculo'}), 400
        
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO vehiculo_eventos (id_vehiculo, id_usuario, tipo, ip, user_agent)
            VALUES (%s, %s, 'whatsapp_click', %s, %s)
        """, (
            id_vehiculo,
            session.get('usuario_id'),
            request.remote_addr,
            request.headers.get('User-Agent', '')[:255]
        ))
        conexion.commit()
        cursor.close()
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error registrando WhatsApp click: {e}")
        try: conexion.rollback()
        except: pass
        return jsonify({'ok': False}), 500

# ---------------------------------------------------------
# MÓDULOS DEL PANEL DEL VENDEDOR (SIDEBAR)
# ---------------------------------------------------------

@vendedor_bp.route('/analytics')
@login_requerido_vendedor
def analytics():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    vistas_mes = 0
    total_consultas = 0
    total_favoritos = 0
    total_whatsapp = 0
    rating_promedio = 0
    vistas_por_dia = []
    top_vehiculos = []
    tabla_vehiculos = []
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Vistas totales acumuladas de todos los vehículos del vendedor
        cursor.execute("""
            SELECT COALESCE(SUM(vistas), 0) AS v FROM vehiculos 
            WHERE id_usuario = %s AND estado != 'eliminado'
        """, (uid,))
        vistas_mes = (cursor.fetchone() or {}).get('v', 0) or 0
        
        # Total consultas (mensajes recibidos como vendedor)
        try:
            cursor.execute("""
                SELECT COUNT(*) AS c FROM conversaciones WHERE id_vendedor = %s
            """, (uid,))
            total_consultas = (cursor.fetchone() or {}).get('c', 0)
        except Exception:
            total_consultas = 0
        
        # Total favoritos a sus vehículos
        try:
            cursor.execute("""
                SELECT COUNT(*) AS c FROM favoritos f
                JOIN vehiculos v ON f.id_vehiculo = v.id
                WHERE v.id_usuario = %s
            """, (uid,))
            total_favoritos = (cursor.fetchone() or {}).get('c', 0)
        except Exception:
            total_favoritos = 0
        
        # Total WhatsApp clicks este mes
        try:
            cursor.execute("""
                SELECT COUNT(*) AS c FROM vehiculo_eventos e
                JOIN vehiculos v ON e.id_vehiculo = v.id
                WHERE v.id_usuario = %s
                  AND e.tipo = 'whatsapp_click'
                  AND e.fecha >= date_trunc('month', CURRENT_DATE)
            """, (uid,))
            total_whatsapp = (cursor.fetchone() or {}).get('c', 0) or 0
        except Exception:
            total_whatsapp = 0
        
        # Rating promedio
        try:
            cursor.execute("""
                SELECT COALESCE(ROUND(AVG(estrellas)::numeric, 1), 5.0) AS r 
                FROM resenas WHERE id_calificado = %s
            """, (uid,))
            rating_promedio = (cursor.fetchone() or {}).get('r', 5.0) or 5.0
        except Exception:
            rating_promedio = 5.0
        
        # Vistas por día (últimos 30 días basadas en publicación — fallback real)
        cursor.execute("""
            SELECT CAST(fecha_publicacion AS DATE) AS dia, COALESCE(SUM(vistas), 0) AS total
            FROM vehiculos
            WHERE id_usuario = %s AND fecha_publicacion >= CURRENT_DATE - INTERVAL '30 DAY'
            GROUP BY dia ORDER BY dia ASC
        """, (uid,))
        for row in cursor.fetchall():
            vistas_por_dia.append({'dia': str(row['dia']), 'total': int(row['total'] or 0)})
        
        # Tabla detallada por vehículo (vistas + WhatsApp clicks + favoritos + precio vs mercado)
        cursor.execute("""
            SELECT 
                v.id,
                v.slug,
                v.vistas,
                v.precio,
                v.anio,
                v.estado,
                m.nombre AS marca,
                mo.nombre AS modelo,
                COALESCE((
                    SELECT COUNT(*) FROM favoritos f WHERE f.id_vehiculo = v.id
                ), 0) AS favoritos_count,
                COALESCE((
                    SELECT COUNT(*) FROM vehiculo_eventos e 
                    WHERE e.id_vehiculo = v.id AND e.tipo = 'whatsapp_click'
                ), 0) AS whatsapp_count,
                COALESCE((
                    SELECT ROUND(AVG(v2.precio)::numeric, 0) FROM vehiculos v2
                    JOIN marcas m2 ON v2.id_marca = m2.id
                    WHERE m2.id = v.id_marca
                      AND v2.anio BETWEEN v.anio - 2 AND v.anio + 2
                      AND v2.id != v.id
                      AND v2.estado IN ('disponible', 'activo')
                      AND v2.precio > 0
                ), 0) AS precio_mercado
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s AND (v.estado IS NULL OR v.estado != 'eliminado')
            ORDER BY v.vistas DESC NULLS LAST
            LIMIT 20
        """, (uid,))
        tabla_vehiculos = cursor.fetchall()
        
        # Top 5 vehículos más vistos (para el gráfico)
        top_vehiculos = list(tabla_vehiculos)[:5]
        
        cursor.close()
    except Exception as e:
        print(f"Error en analytics vendedor: {e}")
        traceback.print_exc()
        try: conexion.rollback()
        except: pass
    finally:
        try: cursor.close()
        except: pass
    
    return render_template('vendedor/analytics.html', 
        vendedor=vendedor, 
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend,
        vistas_mes=vistas_mes,
        total_consultas=total_consultas,
        total_favoritos=total_favoritos,
        total_whatsapp=total_whatsapp,
        rating_promedio=rating_promedio,
        vistas_por_dia=vistas_por_dia,
        top_vehiculos=top_vehiculos,
        tabla_vehiculos=tabla_vehiculos)


@vendedor_bp.route('/publicar')
@login_requerido_vendedor
def publicar():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, _ = _get_vendedor_base(uid)
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, nombre FROM tipos_vehiculos ORDER BY nombre ASC")
        tipos = cursor.fetchall()
        cursor.execute("SELECT id, nombre FROM colores ORDER BY nombre ASC")
        colores = cursor.fetchall()
        cursor.execute("SELECT id, nombre FROM caracteristicas ORDER BY nombre ASC")
        caracteristicas = cursor.fetchall()
    except Exception as e:
        print(f"Error en publicar (vendedor): {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        tipos, colores, caracteristicas = [], [], []
    finally:
        try:
            cursor.close()
        except:
            pass
        
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    return render_template('vendedor/publicar.html', 
        vendedor=vendedor,
        tipos=tipos,
        colores=colores,
        caracteristicas=caracteristicas,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend)

@vendedor_bp.route('/vehiculos')
@login_requerido_vendedor
def mis_vehiculos():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, _ = _get_vendedor_base(uid)
    ultimos_vehiculos = []
    totales = {'activos':0, 'pausados':0, 'vendidos':0, 'vistas':0}
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT v.*, m.nombre as marca_nombre, mo.nombre as modelo_nombre,
            COALESCE(
                (SELECT url_imagen FROM imagenes_vehiculos iv WHERE iv.id_vehiculo = v.id LIMIT 1),
                'img/default_car.jpg'
            ) AS imagen
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY v.fecha_publicacion DESC
        """, (uid,))
        ultimos_vehiculos = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE estado IS NULL OR estado NOT IN ('vendido', 'pausado')) as activos,
                COUNT(*) FILTER (WHERE estado = 'pausado') as pausados,
                COUNT(*) FILTER (WHERE estado = 'vendido') as vendidos,
                COALESCE(SUM(vistas), 0) as vistas
            FROM vehiculos WHERE id_usuario = %s
        """, (uid,))
        res = cursor.fetchone()
        if res:
            totales['activos'] = res.get('activos', 0)
            totales['pausados'] = res.get('pausados', 0)
            totales['vendidos'] = res.get('vendidos', 0)
            totales['vistas'] = res.get('vistas', 0)
            
        cursor.execute("""
            SELECT SUM(vistas) as v FROM vehiculos 
            WHERE id_usuario = %s AND EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE)
        """, (uid,))
        v = (cursor.fetchone() or {}).get('v')
        vistas_mes = v if v else 0
        
        cursor.execute("""
            SELECT COUNT(*) AS c FROM favoritos f
            JOIN vehiculos v ON f.id_vehiculo = v.id
            WHERE v.id_usuario = %s
        """, (uid,))
        total_favoritos = (cursor.fetchone() or {}).get('c', 0)
        
        cursor.execute("""
            SELECT COUNT(*) AS c FROM mensajes m
            JOIN conversaciones c ON m.id_conversacion = c.id
            WHERE (c.id_vendedor = %s OR c.id_comprador = %s)
              AND m.id_remitente != %s AND m.leido = false
        """, (uid, uid, uid))
        mensajes_no_leidos = (cursor.fetchone() or {}).get('c', 0)
        

    except Exception as e:
        print(f"Error cargar mis_vehiculos (vendedor): {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
    finally:
        try:
            cursor.close()
        except:
            pass

    # Obtener Notificaciones (Reales)
    notificaciones_reales = []
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notificaciones WHERE id_usuario = %s AND leida = FALSE ORDER BY fecha_creacion DESC LIMIT 5", (uid,))
        notificaciones_reales = cursor.fetchall()
        cursor.close()
    except:
        pass

    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    market_insight = _get_market_insight(uid)

    return render_template('vendedor/mis_vehiculos.html',
        vendedor=vendedor,
        ultimos_vehiculos=ultimos_vehiculos,
        market_insight=market_insight,
        totales=totales,
        total_vehiculos=totales.get('activos', 0),
        vistas_mes=vistas_mes if 'vistas_mes' in locals() else 0,
        total_favoritos=total_favoritos if 'total_favoritos' in locals() else 0,
        mensajes_no_leidos=mensajes_no_leidos if 'mensajes_no_leidos' in locals() else 0,
        notificaciones=notificaciones_reales,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend,
        sync_version="v3.0 Sync")

@vendedor_bp.route('/editar/<int:vid>', methods=['GET', 'POST'])
@login_requerido_vendedor
def editar_vehiculo(vid):
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Verificar propiedad y obtener datos del vehículo (incluye nombres)
        cursor.execute("""
            SELECT v.*, m.nombre AS marca_nombre, mo.nombre AS modelo_nombre
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id = %s AND v.id_usuario = %s
        """, (vid, uid))
        vehiculo = cursor.fetchone()
        
        if not vehiculo:
            flash("El vehículo solicitado no se encuentra registrado o no cuenta con los permisos de edición necesarios.", "error")
            return redirect(url_for('vendedor.mis_vehiculos'))
            
        if vehiculo.get('estado') == 'bloqueado':
            flash("Este vehículo ha sido restringido por la administración. Por favor, póngase en contacto con el servicio de soporte para más información.", "error")
            return redirect(url_for('vendedor.mis_vehiculos'))
            
        if request.method == 'POST':
            precio = request.form.get('precio')
            kilometraje = request.form.get('kilometraje')
            ciudad_venta = request.form.get('ciudad_venta')
            negociable = 'Si' if request.form.get('negociable') else 'No'
            version = request.form.get('version')
            descripcion = request.form.get('descripcion')
            anio = request.form.get('anio')
            placa = request.form.get('placa', '').strip().upper() if request.form.get('placa') else None
            transmision = request.form.get('transmision') or None
            combustible = request.form.get('combustible') or None
            motor = request.form.get('motor') or None
            traccion = request.form.get('traccion') or None
            puertas = request.form.get('puertas') or None

            # Validaciones ligeras para no romper lo existente
            if anio:
                try:
                    anio_int = int(anio)
                    current_year = datetime.today().year + 1
                    if anio_int < 1950 or anio_int > current_year:
                        flash("El año ingresado debe encontrarse en el rango de 1950 hasta el año en curso.", "error")
                        return redirect(url_for('vendedor.editar_vehiculo', vid=vid))
                    anio = anio_int
                except ValueError:
                    flash("El campo de año requiere un formato numérico válido.", "error")
                    return redirect(url_for('vendedor.editar_vehiculo', vid=vid))
            
            cursor.execute("""
                UPDATE vehiculos 
                SET precio = %s, kilometraje = %s, ciudad_venta = %s, negociable = %s,
                    version = COALESCE(%s, version),
                    descripcion = COALESCE(%s, descripcion),
                    anio = COALESCE(%s, anio),
                    placa = COALESCE(%s, placa),
                    transmision = %s, combustible = %s, motor = %s, traccion = %s, puertas = %s
                WHERE id = %s AND id_usuario = %s
            """, (precio, kilometraje, ciudad_venta, negociable, version, descripcion, anio, placa,
                  transmision, combustible, motor, traccion, puertas, vid, uid))
            
            conexion.commit()
            flash("La información del vehículo ha sido actualizada satisfactoriamente.", "success")
            return redirect(url_for('vendedor.editar_vehiculo', vid=vid))
            
        # 2. Obtener imágenes
        cursor.execute("SELECT * FROM imagenes_vehiculos WHERE id_vehiculo = %s ORDER BY id ASC", (vid,))
        imagenes = cursor.fetchall()
        
        cursor.close()
    except Exception as e:
        print(f"Error en editar_vehiculo: {e}")
        conexion.rollback()
        flash("Se ha presentado un error técnico al procesar la actualización del registro.", "error")
        return redirect(url_for('vendedor.mis_vehiculos'))
    finally:
        try: cursor.close()
        except: pass
        
    return render_template('vendedor/editar_vehiculo.html',
        vendedor=vendedor,
        vehiculo=vehiculo,
        imagenes=imagenes,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend)


@vendedor_bp.route('/vehiculo/<int:vid>/imagenes', methods=['POST'])
@login_requerido_vendedor
def subir_imagen_vehiculo(vid):
    uid = session['usuario_id']
    file = request.files.get('imagen')

    if not file or file.filename == '':
        flash("No se ha detectado ningún archivo de imagen para procesar.", "warning")
        return redirect(url_for('vendedor.editar_vehiculo', vid=vid))

    if not allowed_image(file.filename):
        flash("El formato de archivo no es válido. Formatos permitidos: PNG, JPG, JPEG, GIF, WEBP.", "error")
        return redirect(url_for('vendedor.editar_vehiculo', vid=vid))

    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT 1 FROM vehiculos WHERE id = %s AND id_usuario = %s", (vid, uid))
        if not cursor.fetchone():
            flash("No cuenta con las credenciales necesarias para modificar este registro.", "error")
            return redirect(url_for('vendedor.mis_vehiculos'))

        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'vehiculos')
        os.makedirs(upload_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}_{filename}"
        path_full = os.path.join(upload_dir, filename)
        file.save(path_full)
        
        # APLICAR MARCA DE AGUA AUTOMÁTICA
        apply_watermark(path_full)

        # SUBIR A CLOUDINARY
        from helpers.cloudinary_utils import upload_file_to_cloudinary
        secure_url = upload_file_to_cloudinary(path_full, folder="drivemarket/vehiculos")

        if secure_url:
            cursor.execute("INSERT INTO imagenes_vehiculos (id_vehiculo, url_imagen) VALUES (%s, %s)", (vid, secure_url))
            conexion.commit()
            flash("Imagen subida y procesada correctamente en la nube.", "success")
        else:
            flash("Error técnico al subir la imagen a la nube.", "error")
        
        # Eliminar archivo local temporal si se desea:
        try: os.remove(path_full)
        except: pass

        cursor.close()
    except Exception as e:
        print(f"Error subiendo imagen: {e}")
        try: conexion.rollback()
        except: pass
        flash("No fue posible completar la carga de la imagen en este momento.", "error")

    return redirect(url_for('vendedor.editar_vehiculo', vid=vid))


@vendedor_bp.route('/vehiculo/<int:vid>/imagenes/<int:img_id>/delete', methods=['POST'])
@login_requerido_vendedor
def eliminar_imagen_vehiculo(vid, img_id):
    uid = session['usuario_id']
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT iv.url_imagen 
            FROM imagenes_vehiculos iv
            JOIN vehiculos v ON v.id = iv.id_vehiculo
            WHERE iv.id = %s AND iv.id_vehiculo = %s AND v.id_usuario = %s
        """, (img_id, vid, uid))
        row = cursor.fetchone()
        if not row:
            flash("No se ha localizado la imagen o no tiene permisos de eliminación.", "error")
            return redirect(url_for('vendedor.editar_vehiculo', vid=vid))

        cursor.execute("DELETE FROM imagenes_vehiculos WHERE id = %s", (img_id,))
        conexion.commit()
        cursor.close()

        # Borrar archivo físico
        try:
            file_path = os.path.join(current_app.root_path, 'static', row['url_imagen'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"No se pudo borrar archivo físico: {e}")

        flash("Imagen eliminada.", "success")
    except Exception as e:
        print(f"Error eliminando imagen {img_id}: {e}")
        try: conexion.rollback()
        except: pass
        flash("Error técnico al intentar eliminar el archivo de imagen.", "error")

    return redirect(url_for('vendedor.editar_vehiculo', vid=vid))

@vendedor_bp.route('/vehiculo/<int:vid>/estado', methods=['POST'])
@login_requerido_vendedor
def cambiar_estado_vehiculo(vid):
    uid = session['usuario_id']
    nuevo_estado = request.form.get('estado')
    
    if not nuevo_estado:
        return json.dumps({'ok': False, 'msg': 'Estado no proporcionado'}), 400
        
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar estado actual
        cursor.execute("SELECT estado FROM vehiculos WHERE id = %s AND id_usuario = %s", (vid, uid))
        veh_actual = cursor.fetchone()
        if not veh_actual:
            return json.dumps({'ok': False, 'msg': 'Vehículo no encontrado'}), 404
            
        if veh_actual.get('estado') == 'bloqueado':
            return json.dumps({'ok': False, 'msg': 'Vehículo bloqueado por administración. Contacta con soporte para resolverlo.'}), 403

        cursor.execute("""
            UPDATE vehiculos 
            SET estado = %s 
            WHERE id = %s AND id_usuario = %s
        """, (nuevo_estado, vid, uid))
        conexion.commit()
        cursor.close()
        return json.dumps({'ok': True, 'msg': 'Estado actualizado'})
    except Exception as e:
        print(f"Error cambiando estado (vendedor): {e}")
        conexion.rollback()
        return json.dumps({'ok': False, 'msg': str(e)}), 500
    finally:
        try: cursor.close()
        except: pass

@vendedor_bp.route('/clientes')
@login_requerido_vendedor
def clientes():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, _ = _get_vendedor_base(uid)
    lista_clientes = []
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT u.id, u.nombre, u.email, u.foto,
            MAX(m.fecha_envio) as ultimo_contacto,
            COUNT(m.id) as total_mensajes
            FROM usuarios u
            JOIN mensajes m ON m.id_remitente = u.id
            JOIN conversaciones c ON c.id = m.id_conversacion
            WHERE c.id_vendedor = %s AND m.id_remitente != %s
            GROUP BY u.id, u.nombre, u.email, u.foto
            ORDER BY ultimo_contacto DESC
        """, (uid, uid))
        lista_clientes = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error en modulo clientes: {e}")
        traceback.print_exc()
        try: conexion.rollback()
        except: pass
    finally:
        try: cursor.close()
        except: pass
        
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    return render_template('vendedor/clientes.html', 
        vendedor=vendedor, 
        clientes=lista_clientes,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend)

# Módulos de Comunicación
@vendedor_bp.route('/mensajes-chat')
@login_requerido_vendedor
def mensajes():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, _ = _get_vendedor_base(uid)
    conversaciones = []
    mensajes_chat = []
    id_conv_activa = request.args.get('conv')
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT c.id, c.id_vehiculo as vehiculo_id,
                   m.nombre as marca, mo.nombre as modelo,
                   CASE 
                       WHEN c.id_vendedor = %s THEN u_comp.nombre 
                       ELSE u_vend.nombre 
                   END as interlocutor_nombre,
                   CASE 
                       WHEN c.id_vendedor = %s THEN u_comp.foto 
                       ELSE u_vend.foto 
                   END as interlocutor_foto,
                   (SELECT contenido FROM mensajes WHERE id_conversacion = c.id ORDER BY fecha_envio DESC LIMIT 1) as ultimo_msg,
                   (SELECT fecha_envio FROM mensajes WHERE id_conversacion = c.id ORDER BY fecha_envio DESC LIMIT 1) as ultima_actividad,
                   (SELECT COUNT(*) FROM mensajes WHERE id_conversacion = c.id AND id_remitente != %s AND leido = false) as no_leidos
            FROM conversaciones c
            JOIN vehiculos v ON c.id_vehiculo = v.id
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            JOIN usuarios u_comp ON c.id_comprador = u_comp.id
            JOIN usuarios u_vend ON c.id_vendedor = u_vend.id
            WHERE (c.id_vendedor = %s OR c.id_comprador = %s) AND c.eliminada_vendedor = FALSE
            ORDER BY ultima_actividad DESC NULLS LAST
        """, (uid, uid, uid, uid, uid))
        conversaciones = cursor.fetchall()
        
        if id_conv_activa:
            cursor.execute("SELECT * FROM mensajes WHERE id_conversacion = %s ORDER BY fecha_envio ASC", (id_conv_activa,))
            mensajes_chat = cursor.fetchall()
            cursor.execute("UPDATE mensajes SET leido = true WHERE id_conversacion = %s AND id_remitente != %s", (id_conv_activa, uid))
            conexion.commit()
            
        cursor.close()
    except Exception as e:
        print(f"Error en mensajes vendedor: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
    finally:
        try:
            cursor.close()
        except:
            pass
        
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    mensajes_no_leidos = sum(1 for c in conversaciones if c.get('no_leidos') and c['no_leidos'] > 0) if conversaciones else 0
    return render_template('vendedor/mensajes.html',
        vendedor=vendedor,
        conversaciones=conversaciones,
        mensajes_chat=mensajes_chat,
        id_conv_activa=int(id_conv_activa) if id_conv_activa else None,
        usuario_id=uid,
        mensajes_no_leidos=mensajes_no_leidos,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend)

@vendedor_bp.route('/enviar_mensaje', methods=['POST'])
@login_requerido_vendedor
def enviar_mensaje():
    uid = session['usuario_id']
    id_conversacion = request.form.get('id_conversacion')
    contenido = request.form.get('contenido')
    
    if id_conversacion and contenido:
        try:
            cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT id_comprador, id_vendedor FROM conversaciones WHERE id = %s", (id_conversacion,))
            conv = cursor.fetchone()
            if conv:
                destinatario = conv['id_comprador'] if uid == conv['id_vendedor'] else conv['id_vendedor']
                cursor.execute("""
                    INSERT INTO mensajes (id_conversacion, id_remitente, contenido, leido)
                    VALUES (%s, %s, %s, false)
                """, (id_conversacion, uid, contenido))
                conexion.commit()
        except Exception as e:
            print(f"Error al enviar mensaje (vendedor): {e}")
            import traceback
            traceback.print_exc()
            try:
                conexion.rollback()
            except:
                pass
        finally:
            try:
                cursor.close()
            except:
                pass
            
    return redirect(url_for('vendedor.mensajes', conv=id_conversacion))

@vendedor_bp.route('/mensajes/conversacion/<int:cid>/eliminar', methods=['POST'])
@login_requerido_vendedor
def eliminar_conversacion(cid):
    uid = session['usuario_id']
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE conversaciones SET eliminada_vendedor = TRUE WHERE id = %s AND id_vendedor = %s", (cid, uid))
        conexion.commit()
        cursor.close()
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error eliminando conversación: {e}")
        conexion.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500

@vendedor_bp.route('/mensajes/conversacion/<int:cid>/marcar-no-leido', methods=['POST'])
@login_requerido_vendedor
def marcar_no_leido(cid):
    uid = session['usuario_id']
    try:
        cursor = conexion.cursor()
        # Buscamos el último mensaje del interlocutor para marcarlo como no leído
        cursor.execute("""
            UPDATE mensajes 
            SET leido = FALSE 
            WHERE id = (
                SELECT id FROM mensajes 
                WHERE id_conversacion = %s AND id_remitente != %s
                ORDER BY fecha_envio DESC LIMIT 1
            )
        """, (cid, uid))
        conexion.commit()
        cursor.close()
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error marcando como no leído: {e}")
        conexion.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500

@vendedor_bp.route('/alertas')
@login_requerido_vendedor
def notificaciones():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, _ = _get_vendedor_base(uid)
    notifs = []
    total_no_leidas = 0
    total_vehiculos = 0
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM notificaciones WHERE id_usuario = %s ORDER BY fecha_creacion DESC", (uid,))
        notifs = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as c FROM notificaciones WHERE id_usuario = %s AND leida = false", (uid,))
        res1 = cursor.fetchone()
        if res1: total_no_leidas = res1['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM vehiculos WHERE id_usuario = %s", (uid,))
        res2 = cursor.fetchone()
        if res2: total_vehiculos = res2['c']
        cursor.close()
    except Exception as e:
        print(f"Error en notificaciones vendedor: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
    finally:
        try:
            cursor.close()
        except:
            pass
        
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    return render_template('vendedor/notificaciones.html', 
        vendedor=vendedor,
        notificaciones=notifs,
        total_no_leidas=total_no_leidas,
        total_vehiculos=total_vehiculos,
        estado_verificacion=estado_verificacion,
        perfil_vend=perfil_vend)

# =========================================================
# PEDIDOS — Consultas reales de compradores
# =========================================================
@vendedor_bp.route('/pedidos')
@login_requerido_vendedor
def pedidos():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    conversaciones = []
    total_consultas = 0
    consultas_no_leidas = 0
    total_vehiculos = 0
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Conversaciones del vendedor con datos del vehículo, comprador, etc.
        cursor.execute("""
            SELECT c.id, c.id_vehiculo AS vehiculo_id,
                   m.nombre AS marca, mo.nombre AS modelo,
                   v.precio,
                   u_comp.nombre AS comprador_nombre, u_comp.foto AS comprador_foto,
                   (SELECT contenido FROM mensajes WHERE id_conversacion = c.id ORDER BY fecha_envio DESC LIMIT 1) AS ultimo_msg,
                   (SELECT fecha_envio FROM mensajes WHERE id_conversacion = c.id ORDER BY fecha_envio DESC LIMIT 1) AS ultima_actividad,
                   (SELECT COUNT(*) FROM mensajes WHERE id_conversacion = c.id AND id_remitente != %s AND leido = false) AS no_leidos
            FROM conversaciones c
            JOIN vehiculos v ON c.id_vehiculo = v.id
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            JOIN usuarios u_comp ON c.id_comprador = u_comp.id
            WHERE c.id_vendedor = %s
            ORDER BY ultima_actividad DESC NULLS LAST
        """, (uid, uid))
        conversaciones = cursor.fetchall()
        
        total_consultas = len(conversaciones)
        consultas_no_leidas = sum(1 for c in conversaciones if c.get('no_leidos', 0) and c['no_leidos'] > 0)
        
        # Total vehículos del vendedor
        cursor.execute("SELECT COUNT(*) AS c FROM vehiculos WHERE id_usuario = %s", (uid,))
        total_vehiculos = (cursor.fetchone() or {}).get('c', 0)
        
        cursor.close()
    except Exception as e:
        print(f"Error en pedidos vendedor: {e}")
        traceback.print_exc()
        try: conexion.rollback()
        except: pass
    finally:
        try: cursor.close()
        except: pass
    
    return render_template('vendedor/pedidos.html', 
        vendedor=vendedor, 
        conversaciones=conversaciones,
        total_consultas=total_consultas,
        consultas_no_leidas=consultas_no_leidas,
        total_vehiculos=total_vehiculos,
        estado_verificacion=estado_verificacion, 
        perfil_vend=perfil_vend)

# =========================================================
# FACTURACIÓN — Datos reales de ventas e ingresos
# =========================================================
@vendedor_bp.route('/facturacion')
@login_requerido_vendedor
def facturacion():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    ingresos_totales = 0
    facturas_emitidas = 0
    facturas_cobradas = 0
    por_cobrar = 0
    vehiculos_vendidos = []
    ingresos_por_mes = []
    vehiculos_activos_count = 0
    total_publicaciones = 0
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Ingresos totales (vehículos vendidos)
        cursor.execute("""
            SELECT COALESCE(SUM(precio), 0) AS total, COUNT(*) AS cantidad
            FROM vehiculos WHERE id_usuario = %s AND estado = 'vendido'
        """, (uid,))
        res = cursor.fetchone() or {}
        ingresos_totales = res.get('total', 0) or 0
        facturas_cobradas = res.get('cantidad', 0) or 0
        
        # Vehículos activos (publicaciones activas / potencial ingreso)
        cursor.execute("""
            SELECT COUNT(*) AS c, COALESCE(SUM(precio), 0) AS pot
            FROM vehiculos WHERE id_usuario = %s AND (estado IS NULL OR estado NOT IN ('vendido', 'pausado', 'eliminado'))
        """, (uid,))
        res2 = cursor.fetchone() or {}
        vehiculos_activos_count = res2.get('c', 0) or 0
        por_cobrar = res2.get('pot', 0) or 0
        
        # Total publicaciones (emitidas = activas + vendidas + pausadas)
        cursor.execute("SELECT COUNT(*) AS c FROM vehiculos WHERE id_usuario = %s AND estado != 'eliminado'", (uid,))
        facturas_emitidas = (cursor.fetchone() or {}).get('c', 0) or 0
        
        # Total publicaciones para sidebar
        cursor.execute("SELECT COUNT(*) AS c FROM vehiculos WHERE id_usuario = %s", (uid,))
        total_publicaciones = (cursor.fetchone() or {}).get('c', 0) or 0
        
        # Historial de vehículos vendidos (como "facturas")
        cursor.execute("""
            SELECT v.id, v.precio, v.anio, v.fecha_publicacion, v.estado,
                   m.nombre AS marca, mo.nombre AS modelo,
                   COALESCE(
                       (SELECT u.nombre FROM conversaciones c 
                        JOIN usuarios u ON c.id_comprador = u.id 
                        WHERE c.id_vehiculo = v.id 
                        ORDER BY c.ultima_actividad DESC LIMIT 1),
                       'Comprador directo'
                   ) AS cliente_nombre
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s AND v.estado IN ('vendido', 'activo', 'pausado')
            ORDER BY v.fecha_publicacion DESC
            LIMIT 20
        """, (uid,))
        vehiculos_vendidos = cursor.fetchall()
        
        # Ingresos por mes (últimos 12 meses)
        cursor.execute("""
            SELECT TO_CHAR(fecha_publicacion, 'YYYY-MM') AS mes, 
                   COALESCE(SUM(precio), 0) AS total,
                   COUNT(*) AS cantidad
            FROM vehiculos
            WHERE id_usuario = %s AND estado = 'vendido'
              AND fecha_publicacion >= CURRENT_DATE - INTERVAL '12 MONTH'
            GROUP BY mes ORDER BY mes ASC
        """, (uid,))
        for row in cursor.fetchall():
            ingresos_por_mes.append({
                'mes': row['mes'], 
                'total': float(row['total'] or 0),
                'cantidad': row['cantidad']
            })
        
        cursor.close()
    except Exception as e:
        print(f"Error en facturación vendedor: {e}")
        traceback.print_exc()
        try: conexion.rollback()
        except: pass
    finally:
        try: cursor.close()
        except: pass
    
    return render_template('vendedor/facturacion.html', 
        vendedor=vendedor,
        ingresos_totales=ingresos_totales,
        facturas_emitidas=facturas_emitidas,
        facturas_cobradas=facturas_cobradas,
        por_cobrar=por_cobrar,
        vehiculos_vendidos=vehiculos_vendidos,
        ingresos_por_mes=ingresos_por_mes,
        vehiculos_activos_count=vehiculos_activos_count,
        total_publicaciones=total_publicaciones,
        estado_verificacion=estado_verificacion, 
        perfil_vend=perfil_vend)

# =========================================================
# VERIFICACIÓN — Formulario + procesamiento POST
# =========================================================
@vendedor_bp.route('/verificar', methods=['GET'])
@login_requerido_vendedor
def verificacion():
    uid = session['usuario_id']
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    return render_template('vendedor/verificacion.html', 
        vendedor=vendedor, 
        estado_verificacion=estado_verificacion, 
        perfil_vend=perfil_vend)

@vendedor_bp.route('/solicitar-verificacion', methods=['POST'])
@login_requerido_vendedor
def solicitar_verificacion():
    uid = session['usuario_id']
    
    nombre_tienda = request.form.get('nombre_tienda', '').strip()
    email_comercial = request.form.get('email_comercial', '').strip()
    numero_id = request.form.get('numero_id', '').strip()
    telefono_contacto = request.form.get('telefono_contacto', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    
    if not all([nombre_tienda, email_comercial, numero_id, telefono_contacto, descripcion]):
        flash("Por favor, complete todos los campos requeridos para procesar la verificación.", "error")
        return redirect(url_for('vendedor.verificacion'))
    
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Procesar fotos de cédula
        foto_frontal_path = None
        foto_trasera_path = None
        
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'documentos')
        os.makedirs(upload_dir, exist_ok=True)
        
        foto_frontal = request.files.get('foto_frontal')
        if foto_frontal and foto_frontal.filename:
            ext = foto_frontal.filename.rsplit('.', 1)[-1].lower()
            nombre = f"front_{uid}_{secure_filename(foto_frontal.filename)}"
            foto_frontal.save(os.path.join(upload_dir, nombre))
            foto_frontal_path = f"uploads/documentos/{nombre}"
        
        foto_trasera = request.files.get('foto_trasera')
        if foto_trasera and foto_trasera.filename:
            ext = foto_trasera.filename.rsplit('.', 1)[-1].lower()
            nombre = f"back_{uid}_{secure_filename(foto_trasera.filename)}"
            foto_trasera.save(os.path.join(upload_dir, nombre))
            foto_trasera_path = f"uploads/documentos/{nombre}"
        
        # Verificar si ya existe un perfil de vendedor
        cursor.execute("SELECT id, foto_id_frontal, foto_id_trasera FROM perfil_vendedor WHERE usuario_id = %s", (uid,))
        perfil_existente = cursor.fetchone()
        
        if perfil_existente:
            # Usar las fotos existentes si no se suben nuevas
            if not foto_frontal_path:
                foto_frontal_path = perfil_existente.get('foto_id_frontal')
            if not foto_trasera_path:
                foto_trasera_path = perfil_existente.get('foto_id_trasera')
                
            cursor.execute("""
                UPDATE perfil_vendedor SET 
                    nombre_tienda = %s, email_comercial = %s, numero_id = %s,
                    telefono_contacto = %s, descripcion = %s,
                    foto_id_frontal = %s, foto_id_trasera = %s,
                    estado_verificacion = 'pendiente'
                WHERE usuario_id = %s
            """, (nombre_tienda, email_comercial, numero_id, telefono_contacto, 
                  descripcion, foto_frontal_path, foto_trasera_path, uid))
        else:
            cursor.execute("""
                INSERT INTO perfil_vendedor 
                    (usuario_id, nombre_tienda, email_comercial, numero_id, telefono_contacto, 
                     descripcion, foto_id_frontal, foto_id_trasera, estado_verificacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
            """, (uid, nombre_tienda, email_comercial, numero_id, telefono_contacto,
                  descripcion, foto_frontal_path, foto_trasera_path))
        
        conexion.commit()
        flash("La solicitud de verificación ha sido recibida y se encuentra en proceso de revisión administrativa.", "success")
        
    except Exception as e:
        print(f"Error en solicitar_verificacion: {e}")
        traceback.print_exc()
        try: conexion.rollback()
        except: pass
        flash("Se presentó un inconveniente al procesar su solicitud de verificación.", "error")
    finally:
        try: cursor.close()
        except: pass
    
    return redirect(url_for('vendedor.verificacion'))

# =========================================================
# AJUSTES — Perfil, Empresa, Contraseña (GET + POST)
# =========================================================
@vendedor_bp.route('/configuracion', methods=['GET', 'POST'])
@login_requerido_vendedor
def ajustes():
    uid = session['usuario_id']
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        try:
            cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            if accion == 'perfil':
                nombre = request.form.get('nombre', '').strip()
                apellidos = request.form.get('apellidos', '').strip()
                telefono = request.form.get('telefono', '').strip()
                
                # Procesar foto de perfil
                foto_file = request.files.get('foto_user')
                if foto_file and foto_file.filename:
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'usuarios')
                    os.makedirs(upload_dir, exist_ok=True)
                    ext = foto_file.filename.rsplit('.', 1)[-1].lower()
                    nombre_archivo = f"user_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
                    foto_file.save(os.path.join(upload_dir, nombre_archivo))
                    cursor.execute("UPDATE usuarios SET foto = %s WHERE id = %s", (nombre_archivo, uid))
                
                cursor.execute("""
                    UPDATE usuarios SET nombre = %s, apellidos = %s, telefono = %s 
                    WHERE id = %s
                """, (nombre, apellidos, telefono, uid))
                
                conexion.commit()
                session['nombre'] = nombre
                flash("Los datos de su perfil han sido actualizados exitosamente.", "success")
                
            elif accion == 'empresa':
                nombre_empresa = request.form.get('nombre_empresa', '').strip()
                nit = request.form.get('nit', '').strip()
                telefono = request.form.get('telefono', '').strip()
                direccion = request.form.get('direccion', '').strip()
                descripcion = request.form.get('descripcion', '').strip()
                
                # Actualizar datos de empresa en usuarios (sin NIT porque pertenece al perfil de vendedor)
                cursor.execute("""
                    UPDATE usuarios SET nombre_empresa = %s, telefono = %s
                    WHERE id = %s
                """, (nombre_empresa, telefono, uid))
                
                # Actualizar o insertar perfil_vendedor (ahora incluye numero_id que equivale al NIT)
                cursor.execute("SELECT id FROM perfil_vendedor WHERE usuario_id = %s", (uid,))
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE perfil_vendedor SET direccion_negocio = %s, descripcion = %s, numero_id = %s
                        WHERE usuario_id = %s
                    """, (direccion, descripcion, nit, uid))
                else:
                    cursor.execute("""
                        INSERT INTO perfil_vendedor (usuario_id, nombre_tienda, email_comercial, numero_id, 
                            descripcion, direccion_negocio, estado_verificacion)
                        VALUES (%s, %s, '', %s, %s, %s, 'pendiente')
                    """, (uid, nombre_empresa, nit, descripcion, direccion))
                
                # Procesar logo de tienda
                foto_tienda = request.files.get('foto')
                if foto_tienda and foto_tienda.filename:
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'vendedores')
                    os.makedirs(upload_dir, exist_ok=True)
                    ext = foto_tienda.filename.rsplit('.', 1)[-1].lower()
                    nombre_logo = f"logo_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
                    foto_tienda.save(os.path.join(upload_dir, nombre_logo))
                    cursor.execute("UPDATE perfil_vendedor SET logo_tienda = %s WHERE usuario_id = %s", (nombre_logo, uid))
                
                # Procesar foto de portada
                foto_portada = request.files.get('foto_portada')
                if foto_portada and foto_portada.filename:
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'portadas')
                    os.makedirs(upload_dir, exist_ok=True)
                    ext = foto_portada.filename.rsplit('.', 1)[-1].lower()
                    nombre_portada = f"cover_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
                    foto_portada.save(os.path.join(upload_dir, nombre_portada))
                    cursor.execute("UPDATE perfil_vendedor SET foto_portada = %s WHERE usuario_id = %s", (nombre_portada, uid))
                
                conexion.commit()
                flash("La información de la empresa ha sido registrada satisfactoriamente.", "success")
                
            elif accion == 'password':
                password_actual = request.form.get('password_actual', '')
                password_nueva = request.form.get('password_nueva', '')
                password_confirmar = request.form.get('password_confirmar', '')
                
                if len(password_nueva) < 8:
                    flash("La nueva contraseña debe cumplir con una longitud mínima de 8 caracteres.", "error")
                    return redirect(url_for('vendedor.ajustes'))
                
                if password_nueva != password_confirmar:
                    flash("La confirmación de la contraseña no coincide con el campo ingresado.", "error")
                    return redirect(url_for('vendedor.ajustes'))
                
                # Verificar contraseña actual
                cursor.execute("SELECT password FROM usuarios WHERE id = %s", (uid,))
                user_data = cursor.fetchone()
                
                if not user_data or not check_password_hash(user_data['password'], password_actual):
                    flash("La contraseña proporcionada actualmente es incorrecta.", "error")
                    return redirect(url_for('vendedor.ajustes'))
                
                # Actualizar contraseña
                nuevo_hash = generate_password_hash(password_nueva)
                cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (nuevo_hash, uid))
                conexion.commit()
                flash("Su contraseña de acceso ha sido modificada correctamente.", "success")
                
            cursor.close()
        except Exception as e:
            print(f"Error en ajustes POST: {e}")
            traceback.print_exc()
            try: conexion.rollback()
            except: pass
            flash("Se ha producido un error al intentar guardar las modificaciones realizadas.", "error")
        finally:
            try: cursor.close()
            except: pass
        
        return redirect(url_for('vendedor.ajustes'))
    
    # GET: Obtener datos completos del vendedor
    vendedor, _, _, estado_verificacion, perfil_vend = _get_vendedor_base(uid)
    
    # Obtener datos adicionales de empresa
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT u.*, pv.logo_tienda, pv.foto_portada, pv.direccion_negocio
            FROM usuarios u 
            LEFT JOIN perfil_vendedor pv ON u.id = pv.usuario_id
            WHERE u.id = %s
        """, (uid,))
        vendedor_full = cursor.fetchone()
        if vendedor_full:
            vendedor.update(vendedor_full)
        cursor.close()
    except Exception as e:
        print(f"Error cargando datos ajustes: {e}")
        try: conexion.rollback()
        except: pass
    finally:
        try: cursor.close()
        except: pass
    
    return render_template('vendedor/ajustes.html', 
        vendedor=vendedor, 
        estado_verificacion=estado_verificacion, 
        perfil_vend=perfil_vend)

@vendedor_bp.route('/solicitar-destacado/<int:id>', methods=['POST'])
@login_requerido_vendedor
def solicitar_destacado(id):
    """Sube el comprobante de pago para poner el vehículo en estado pendiente de verificación para destacado"""
    from app import app
    from werkzeug.utils import secure_filename
    import os
    import time
    
    uid = session.get('usuario_id')
    comprobante = request.files.get('comprobante')
    
    if not comprobante or comprobante.filename == '':
        flash("Se requiere adjuntar un comprobante de pago legible para continuar.", "error")
        return redirect(url_for('vendedor.mis_vehiculos'))
        
    try:
        # Verificar que el vehículo pertenece a este usuario
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM vehiculos WHERE id = %s AND id_usuario = %s", (id, uid))
        if not cursor.fetchone():
            cursor.close()
            flash("No se ha localizado el vehículo o no cuenta con autorización de gestión.", "error")
            return redirect(url_for('vendedor.mis_vehiculos'))
            
        # Crear directorio de comprobantes (estático)
        upload_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads', 'comprobantes')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generar nombre único
        ext = comprobante.filename.rsplit('.', 1)[1].lower() if '.' in comprobante.filename else 'jpg'
        filename = secure_filename(f"comprobante_{id}_{int(time.time())}.{ext}")
        filepath = os.path.join(upload_folder, filename)
        
        # Guardar imagen físicamente
        comprobante.save(filepath)
        db_filepath = f"uploads/comprobantes/{filename}"
        
        # Actualizar tabla
        cursor.execute("""
            UPDATE vehiculos 
            SET comprobante_pago = %s, estado_pago = 'pendiente' 
            WHERE id = %s
        """, (db_filepath, id))
        conexion.commit()
        cursor.close()
        
        flash("El comprobante ha sido recibido. Su anuncio entrará en proceso de revisión para ser destacado.", "success")
    except Exception as e:
        print(f"Error al procesar comprobante: {e}")
        try: conexion.rollback()
        except: pass
        flash("Error al procesar la carga del comprobante de pago.", "error")
        
    return redirect(url_for('vendedor.mis_vehiculos'))


