from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from psycopg2 import pool
import psycopg2.extras
from datetime import datetime
from functools import wraps
import contextlib
import os
from dotenv import load_dotenv

notificaciones_bp = Blueprint('notificaciones', __name__)
load_dotenv()

# =================================================================
# CONFIGURACIÓN DE POOL DE CONEXIONES
# =================================================================

connection_pool = pool.SimpleConnectionPool(
    1,
    5,
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "samueladso"),
    dbname=os.getenv("DB_NAME", "todoen1unos"),
    port=int(os.getenv("DB_PORT", "5432"))
)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            if request.is_json: return jsonify({'success': False, 'message': 'No autorizado'}), 401
            flash("Por favor, inicie sesión para visualizar su centro de notificaciones.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@contextlib.contextmanager
def get_db_cursor(dictionary=True):
    connection = connection_pool.getconn()
    connection.autocommit = False
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor if dictionary else None)
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection_pool.putconn(connection)

def format_tiempo_transcurrido(fecha):
    ahora = datetime.now()
    diff = ahora - fecha if isinstance(fecha, datetime) else ahora - datetime.strptime(str(fecha), '%Y-%m-%d %H:%M:%S')
    minutos = diff.total_seconds() / 60
    if minutos < 1: return "Ahora mismo"
    elif minutos < 60: return f"{int(minutos)} min"
    elif minutos < 1440: return f"{int(minutos / 60)} h"
    else: return fecha.strftime('%d/%m/%Y')

# =================================================================
# 1. CENTRO DE NOTIFICACIONES
# =================================================================

@notificaciones_bp.route('/centro-notificaciones')
@login_required
def centro_notificaciones():
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            # 1. Obtener datos del usuario para el sidebar Elite
            cursor.execute("SELECT id, nombre, apellidos, email, foto, username FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_data_row = cursor.fetchone()
            usuario_data = dict(usuario_data_row) if usuario_data_row else {}
            
            # 2. Obtener notificaciones
            cursor.execute("""
                SELECT n.* FROM notificaciones n
                WHERE n.id_usuario = %s
                ORDER BY n.leida ASC, n.fecha_creacion DESC
                LIMIT 50
            """, (usuario_id,))
            notificaciones = [dict(n) for n in cursor.fetchall()]
            for notif in notificaciones:
                notif['tiempo_transcurrido'] = format_tiempo_transcurrido(notif['fecha_creacion'])
            
            # 3. Métricas para las tarjetas Elite
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s AND leida = FALSE", (usuario_id,))
            total_no_leidas = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s", (usuario_id,))
            total_notificaciones = cursor.fetchone()['total']

            # 4. Obtener mensajes no leídos (de la tabla mensajes)
            cursor.execute("""
                SELECT COUNT(*) as total FROM mensajes m
                JOIN conversaciones c ON m.id_conversacion = c.id
                WHERE (c.id_comprador = %s OR c.id_vendedor = %s)
                AND m.id_remitente != %s AND m.leido = FALSE
            """, (usuario_id, usuario_id, usuario_id))
            mensajes_no_leidos = cursor.fetchone()['total']

            # 5. Consultas pendientes (tipo 'consulta' no leída)
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s AND tipo = 'consulta' AND leida = FALSE", (usuario_id,))
            consultas_pendientes = cursor.fetchone()['total']
        
        tipos_notificaciones = {
            'precio_bajo': {'icono': 'fa-tag', 'color': 'success', 'nombre': 'Precio bajo'},
            'mensaje_nuevo': {'icono': 'fa-envelope', 'color': 'primary', 'nombre': 'Mensaje nuevo'},
            'favorito': {'icono': 'fa-heart', 'color': 'danger', 'nombre': 'Favoritos'},
            'vehiculo_vendido': {'icono': 'fa-car', 'color': 'warning', 'nombre': 'Vehículo vendido'},
            'sistema': {'icono': 'fa-cog', 'color': 'secondary', 'nombre': 'Sistema'},
            'consulta': {'icono': 'fa-question-circle', 'color': 'info', 'nombre': 'Consultas'}
        }
        return render_template('notificaciones/centro.html', 
                             notificaciones=notificaciones, 
                             total_no_leidas=total_no_leidas, 
                             total_notificaciones=total_notificaciones,
                             mensajes_no_leidos=mensajes_no_leidos,
                             consultas_pendientes=consultas_pendientes,
                             usuario=usuario_data,
                             tipos_notificaciones=tipos_notificaciones)
    except Exception as e:
        print(f"❌ Error en centro: {e}")
        return redirect(url_for('index'))

# =================================================================
# 2. MARCAR NOTIFICACIÓN COMO LEÍDA
# =================================================================

@notificaciones_bp.route('/marcar-leida/<int:notificacion_id>', methods=['POST'])
@login_required
def marcar_leida(notificacion_id):
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE notificaciones SET leida = TRUE, fecha_leida = NOW() WHERE id = %s AND id_usuario = %s", (notificacion_id, usuario_id))
            resp = jsonify({'success': cursor.rowcount > 0})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500

# =================================================================
# 3. MARCAR TODAS COMO LEÍDAS
# =================================================================

@notificaciones_bp.route('/marcar-todas-leidas', methods=['POST'])
@login_required
def marcar_todas_leidas():
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE notificaciones SET leida = TRUE, fecha_leida = NOW() WHERE id_usuario = %s AND leida = FALSE", (usuario_id,))
            resp = jsonify({'success': True, 'actualizadas': cursor.rowcount})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e: return jsonify({'success': False}), 500

# =================================================================
# 4. ELIMINAR NOTIFICACIÓN
# =================================================================

@notificaciones_bp.route('/eliminar/<int:notificacion_id>', methods=['DELETE'])
@login_required
def eliminar_notificacion(notificacion_id):
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM notificaciones WHERE id = %s AND id_usuario = %s", (notificacion_id, usuario_id))
            resp = jsonify({'success': cursor.rowcount > 0})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e: return jsonify({'success': False}), 500

@notificaciones_bp.route('/eliminar-todas', methods=['DELETE'])
@login_required
def eliminar_todas():
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM notificaciones WHERE id_usuario = %s", (usuario_id,))
            return jsonify({'success': True, 'borradas': cursor.rowcount})
    except Exception as e: return jsonify({'success': False}), 500

# =================================================================
# 5. OBTENER NOTIFICACIONES NO LEÍDAS (AJAX)
# =================================================================

@notificaciones_bp.route('/no-leidas', methods=['GET'])
@login_required
def obtener_no_leidas():
    try:
        usuario_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s AND leida = FALSE", (usuario_id,))
            total_count = cursor.fetchone()['total']
            cursor.execute("SELECT * FROM notificaciones WHERE id_usuario = %s AND leida = FALSE ORDER BY fecha_creacion DESC LIMIT 10", (usuario_id,))
            notificaciones = cursor.fetchall()
            for n in notificaciones: n['tiempo_transcurrido'] = format_tiempo_transcurrido(n['fecha_creacion'])
            
            resp = jsonify({'success': True, 'notificaciones': notificaciones, 'total_unread': total_count})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e: return jsonify({'success': False, 'notificaciones': [], 'total_unread': 0})

# =================================================================
# 6. PAGINACIÓN Y FILTROS
# =================================================================

@notificaciones_bp.route('/pagina/<int:pagina>', methods=['GET'])
@login_required
def obtener_pagina_notificaciones(pagina):
    try:
        usuario_id = session['usuario_id']
        limit = 20
        offset = (pagina - 1) * limit
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM notificaciones WHERE id_usuario = %s ORDER BY leida ASC, fecha_creacion DESC LIMIT %s OFFSET %s", (usuario_id, limit, offset))
            notifs = cursor.fetchall()
            for n in notifs: n['tiempo_transcurrido'] = format_tiempo_transcurrido(n['fecha_creacion'])
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s", (usuario_id,))
            total = cursor.fetchone()['total']
            return jsonify({'success': True, 'notificaciones': notifs, 'pagina_actual': pagina, 'total_paginas': (total + limit - 1) // limit, 'hay_mas': len(notifs) == limit})
    except Exception as e: return jsonify({'success': False, 'notificaciones': []})

@notificaciones_bp.route('/filtrar', methods=['POST'])
@login_required
def filtrar_notificaciones():
    try:
        u_id = session['usuario_id']
        data = request.json
        tipo, leida = data.get('tipo'), data.get('leida')
        q = "SELECT * FROM notificaciones WHERE id_usuario = %s"
        p = [u_id]
        if tipo and tipo != 'todos': q += " AND tipo = %s"; p.append(tipo)
        if leida is not None and leida != 'todos': q += " AND leida = %s"; p.append(leida == 'leidas')
        q += " ORDER BY fecha_creacion DESC"
        with get_db_cursor() as cursor:
            cursor.execute(q, tuple(p))
            notifs = cursor.fetchall()
            for n in notifs: n['tiempo_transcurrido'] = format_tiempo_transcurrido(n['fecha_creacion'])
            return jsonify({'success': True, 'notificaciones': notifs, 'total': len(notifs)})
    except Exception as e: return jsonify({'success': False, 'notificaciones': []})

def crear_notificacion(id_usuario, tipo, titulo, mensaje, url_accion=None, id_relacion=None):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("INSERT INTO notificaciones (id_usuario, tipo, titulo, mensaje, url_accion, id_relacion, fecha_creacion) VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING id", (id_usuario, tipo, titulo, mensaje, url_accion, id_relacion))
            return cursor.fetchone()['id']
    except Exception as e: return None

@notificaciones_bp.route('/marcar-no-leida/<int:notificacion_id>', methods=['POST'])
@login_required
def marcar_no_leida(notificacion_id):
    try:
        u_id = session['usuario_id']
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE notificaciones SET leida = FALSE, fecha_leida = NULL WHERE id = %s AND id_usuario = %s", (notificacion_id, u_id))
            return jsonify({'success': cursor.rowcount > 0})
    except Exception as e: return jsonify({'success': False}), 500

