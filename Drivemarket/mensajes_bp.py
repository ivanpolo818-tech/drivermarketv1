from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify
from db_config import conexion
import psycopg2
import psycopg2.extras
import contextlib
# Crea el Blueprint
mensajes_bp = Blueprint('mensajes', __name__, url_prefix='/mensajes')


# ---------------------------------------------------------------------
# DECORADOR DE REQUERIMIENTO DE LOGIN
# ---------------------------------------------------------------------
def login_requerido(f):
    """Decorador simple para asegurar que el usuario está logueado."""
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            # Asume que 'login' es una ruta definida en app.py
            flash("Por favor, inicie sesión para acceder a su centro de mensajes.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    # Evita errores de redefinición de nombres de función
    decorated_function.__name__ = f.__name__ 
    return decorated_function


from functools import wraps
from flask import session, flash, redirect, url_for

# ----------------------------------------------------
# DECORADOR DE SEGURIDAD
# (Pégalo al inicio de mensajes_bp.py)
# ----------------------------------------------------
def login_activo_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Para continuar, es necesario iniciar sesión en su cuenta.", "warning")
            return redirect(url_for('login'))
        
        # Opcional: Verificar estado si lo guardas en sesión
        estado = session.get('estado')
        if estado == 'bloqueado' or estado == 'inactivo':
             session.clear()
             flash("Su cuenta se encuentra actualmente inactiva o restringida.", "danger")
             return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorador
# ---------------------------------------------------------------------
@contextlib.contextmanager
def get_db_cursor(dictionary=True):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor if dictionary else None)
    try:
        yield cursor
    finally:
        cursor.close()

# ---------------------------------------------------------------------


## 🚀 RUTAS DEL CENTRO DE MENSAJES

### 1. Centro Principal de Mensajes (Lista de Hilos)
@mensajes_bp.route('/', defaults={'id_conversacion': None})
@mensajes_bp.route('/<int:id_conversacion>')
@login_requerido
def centro_mensajes(id_conversacion):
    """Muestra la lista de conversaciones y el chat seleccionado."""
    user_id = session['usuario_id']
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    conversaciones = []
    mensajes = []
    
    try:
        # 1. Obtener todos los hilos donde el usuario es comprador O vendedor
        cursor.execute("""
            SELECT 
                c.id, c.ultima_actividad, c.id_vehiculo,
                mo.nombre AS modelo, 
                m.nombre AS marca, 
                u.nombre AS nombre_interlocutor, u.id AS id_interlocutor,
                (SELECT COUNT(*) FROM mensajes WHERE id_conversacion = c.id AND id_remitente != %s AND leido = false) AS no_leidos
            FROM conversaciones c
            LEFT JOIN vehiculos v ON c.id_vehiculo = v.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id 
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN usuarios u ON u.id = (
                CASE WHEN c.id_comprador = %s THEN c.id_vendedor ELSE c.id_comprador END
            )
            WHERE c.id_comprador = %s OR c.id_vendedor = %s
            ORDER BY c.ultima_actividad DESC
        """, (user_id, user_id, user_id, user_id))
        
        conversaciones = cursor.fetchall()
        
        if id_conversacion:
            hilo_valido = any(c['id'] == id_conversacion for c in conversaciones)
            
            if hilo_valido:
                # Marcar mensajes como leídos
                cursor.execute("UPDATE mensajes SET leido = true WHERE id_conversacion = %s AND id_remitente != %s", (id_conversacion, user_id))
                conexion.commit()

                # Obtener mensajes
                cursor.execute("SELECT id_remitente, contenido, fecha_envio FROM mensajes WHERE id_conversacion = %s ORDER BY fecha_envio ASC", (id_conversacion,))
                mensajes = cursor.fetchall()
        # --- NUEVO: OBTENER DATOS PARA EL DASHBOARD INTEGRADO ---
        # 1. Datos del usuario para el sidebar
        cursor.execute("SELECT id, nombre, apellidos, email, telefono, username, foto FROM usuarios WHERE id = %s", (user_id,))
        usuario_data = cursor.fetchone()

        # 2. Promedio de Valoración (Reseñas)
        cursor.execute("SELECT AVG(estrellas) as avg_rating FROM resenas WHERE id_calificado = %s", (user_id,))
        rating_res = cursor.fetchone()
        avg_rating = round(float(rating_res['avg_rating'] or 5.0), 1)

        # 3. Métricas de mensajes
        unread_total = sum(c['no_leidos'] for c in conversaciones)
        active_conversations = len(conversaciones)
        
        # 4. Tiempo de respuesta (Simple fallback o cálculo básico)
        # Por ahora mostramos "—" o un valor fijo si no hay historial histórico complejo
        resp_time = "—" 
        
    except Exception as e:
        print(f"Error en centro_mensajes: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Se ha presentado un inconveniente al cargar su bandeja de entrada. Por favor, intente de nuevo más tarde.", "error")
        usuario_data = {}
        avg_rating = 0.0
        unread_total = 0
        active_conversations = 0
        resp_time = "—"
    finally:
        try:
            cursor.close()
        except:
            pass

    from datetime import datetime
    return render_template('users/centro_mensajes.html', 
                           usuario=usuario_data,
                           conversaciones=conversaciones,
                           mensajes=mensajes,
                           id_conversacion_actual=id_conversacion,
                           user_id=user_id,
                           now_date=datetime.now().date(),
                           unread_total=unread_total,
                           active_conversations=active_conversations,
                           avg_rating=avg_rating,
                           resp_time=resp_time)


### 2. Iniciar o Abrir un Hilo desde la Vista del Vehículo
@mensajes_bp.route('/iniciar/<int:vehiculo_id>')
@login_requerido
def iniciar_chat(vehiculo_id):
    # ... (El código de lógica para crear el hilo es correcto y se mantiene) ...
    id_comprador = session['usuario_id']
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    id_conversacion = None

    try:
        cursor.execute("SELECT id_usuario FROM vehiculos WHERE id=%s", (vehiculo_id,))
        vehiculo = cursor.fetchone()
        
        if not vehiculo:
            flash("La publicación solicitada no se encuentra disponible.", "error")
            return redirect(url_for('home'))

        id_vendedor = vehiculo['id_usuario']
        
        if id_comprador == id_vendedor:
            flash("Operación no permitida. No puede iniciar un diálogo de consulta sobre su propio vehículo.", "warning")
            return redirect(url_for('detalle', id=vehiculo_id))

        cursor.execute("""
            SELECT id FROM conversaciones 
            WHERE id_vehiculo = %s AND id_comprador = %s
        """, (vehiculo_id, id_comprador))
        conversacion = cursor.fetchone()

        if not conversacion:
            cursor.execute("""
                INSERT INTO conversaciones (id_vehiculo, id_comprador, id_vendedor, fecha_creacion, ultima_actividad)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (vehiculo_id, id_comprador, id_vendedor))
            conexion.commit()
            id_conversacion = cursor.fetchone()['id']
        else:
            id_conversacion = conversacion['id']
            
    except Exception as e:
        print(f"Error en iniciar_chat: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Error al procesar la apertura de la conversación.", "error")
        return redirect(url_for('detalle', id=vehiculo_id))
    finally:
        try:
            cursor.close()
        except:
            pass
    
    return redirect(url_for('mensajes.centro_mensajes', id_conversacion=id_conversacion))


# ----------------------
# Eliminar conversación
# ----------------------
@mensajes_bp.route('/eliminar/<int:id_conversacion>', methods=['POST'])
@login_requerido
def eliminar_conversacion(id_conversacion):
    """Borra un hilo y sus mensajes si el usuario es participante."""
    user_id = session['usuario_id']
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "DELETE FROM conversaciones WHERE id = %s AND (id_comprador = %s OR id_vendedor = %s)",
            (id_conversacion, user_id, user_id)
        )
        if cursor.rowcount > 0:
            cursor.execute("DELETE FROM mensajes WHERE id_conversacion = %s", (id_conversacion,))
            conexion.commit()
            flash("La conversación ha sido eliminada correctamente de su historial.", "success")
        else:
            flash("No se pudo procesar la eliminación de la conversación. Verifique sus permisos.", "warning")
    except Exception as e:
        conexion.rollback()
        flash(f"Error al eliminar la conversación: {e}", "danger")
    finally:
        cursor.close()
    return redirect(url_for('mensajes.centro_mensajes'))

@mensajes_bp.route('/marcar-no-leido/<int:id_conversacion>', methods=['POST'])
@login_requerido
def marcar_no_leido(id_conversacion):
    """Marca como no leídos los mensajes del otro usuario en esta conversación."""
    user_id = session['usuario_id']
    cursor = (conexion.connection if hasattr(conexion, 'connection') else conexion).cursor() # Handle potential different wrapper
    try:
        cursor.execute("""
            UPDATE mensajes 
            SET leido = false 
            WHERE id_conversacion = %s AND id_remitente != %s
        """, (id_conversacion, user_id))
        conexion.commit()
        flash("Conversación marcada como no leída.", "success")
    except Exception as e:
        conexion.rollback()
        flash(f"Error al actualizar estado: {e}", "danger")
    finally:
        cursor.close()
    return redirect(url_for('mensajes.centro_mensajes'))

### 3. Enviar Mensaje (POST)
@mensajes_bp.route('/enviar', methods=['POST'])
@login_requerido
def enviar_mensaje():
    # ... (El código de envío de mensaje es correcto y se mantiene) ...
    user_id = session['usuario_id']
    id_conversacion = request.form.get('id_conversacion', type=int)
    contenido = request.form.get('contenido')

    if not contenido or not id_conversacion or len(contenido.strip()) < 1 or len(contenido) > 500:
        flash("El contenido del mensaje no cumple con los requisitos mínimos de seguridad o formato.", "error")
        return redirect(url_for('mensajes.centro_mensajes', id_conversacion=id_conversacion))

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Verificar que el usuario pertenezca a la conversación
        cursor.execute("SELECT id FROM conversaciones WHERE id = %s AND (id_comprador = %s OR id_vendedor = %s)", (id_conversacion, user_id, user_id))
        
        if not cursor.fetchone():
            flash("No cuenta con la autorización necesaria para participar en este hilo de mensajes.", "error")
            return redirect(url_for('mensajes.centro_mensajes'))

        # Insertar mensaje y actualizar actividad
        cursor.execute("INSERT INTO mensajes (id_conversacion, id_remitente, contenido) VALUES (%s, %s, %s)", (id_conversacion, user_id, contenido))
        cursor.execute("UPDATE conversaciones SET ultima_actividad = NOW() WHERE id = %s", (id_conversacion,))
        
        conexion.commit()
        
    except Exception as e:
        conexion.rollback()
        flash(f"Error al enviar mensaje: {e}", "error")
    finally:
        cursor.close()

    return redirect(url_for('mensajes.centro_mensajes', id_conversacion=id_conversacion))




@mensajes_bp.route('/guardar_resena', methods=['POST'])
@login_activo_requerido
def guardar_resena():
    id_conversacion = request.form.get('id_conversacion')
    calificacion = request.form.get('calificacion')
    comentario = request.form.get('comentario')
    
    usuario_actual = session.get('usuario_id')

    if not usuario_actual:
        flash("Acceso denegado. Se requiere autenticación para realizar esta operación.", "warning")
        return redirect(url_for('login'))

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 1. Obtenemos los participantes usando los nombres REALES de tu tabla
    cursor.execute("""
        SELECT id_comprador, id_vendedor 
        FROM conversaciones 
        WHERE id = %s
    """, (id_conversacion,))
    
    chat = cursor.fetchone()
    
    if chat:
        # 2. Lógica para saber a quién calificar
        if chat['id_comprador'] == usuario_actual:
            id_calificado = chat['id_vendedor']
        else:
            id_calificado = chat['id_comprador']
        
        try:
            # 3. Guardar la reseña
            cursor.execute("""
                INSERT INTO resenas (id_autor, id_calificado, estrellas, comentario, fecha)
                VALUES (%s, %s, %s, %s, NOW())
            """, (usuario_actual, id_calificado, calificacion, comentario))
            
            conexion.commit()
            flash("Agradecemos su feedback. Su reseña ha sido registrada correctamente.", "success")
        except Exception as e:
            print(f"Error al guardar reseña: {e}")
            import traceback
            traceback.print_exc()
            try:
                conexion.rollback()
            except:
                pass
            flash("Error técnico al procesar el registro de la reseña.", "danger")
    else:
        flash("La conversación especificada no se encuentra registrada.", "danger")
    
    try:
        cursor.close()
    except:
        pass
    
    return redirect(url_for('mensajes.centro_mensajes', id_conversacion=id_conversacion))

@mensajes_bp.route('/recientes')
@login_activo_requerido
def mensajes_recientes():
    """Retorna las 5 conversaciones más recientes para el dropdown (JSON)."""
    user_id = session.get('usuario_id')
    if not user_id: return jsonify({'success': False}), 401
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id AS id_conversacion, 
                    c.ultima_actividad, 
                    u.nombre AS nombre_otro,
                    u.foto AS foto_filename,
                    (SELECT contenido FROM mensajes WHERE id_conversacion = c.id ORDER BY fecha_envio DESC LIMIT 1) AS ultimo_mensaje,
                    (SELECT COUNT(*) FROM mensajes WHERE id_conversacion = c.id AND id_remitente != %s AND leido = false) AS no_leidos
                FROM conversaciones c
                JOIN usuarios u ON u.id = (CASE WHEN c.id_comprador = %s THEN c.id_vendedor ELSE c.id_comprador END)
                WHERE c.id_comprador = %s OR c.id_vendedor = %s
                ORDER BY c.ultima_actividad DESC
                LIMIT 5
            """, (user_id, user_id, user_id, user_id))
            
            chats = cursor.fetchall()
            
            # Formatear datos para el JSON del frontend
            from datetime import datetime
            now = datetime.now()
            for chat in chats:
                # 1. Formatear Fecha Relativa
                if chat['ultima_actividad']:
                    if chat['ultima_actividad'].date() == now.date():
                        chat['fecha_relativa'] = chat['ultima_actividad'].strftime('%H:%M')
                    else:
                        chat['fecha_relativa'] = chat['ultima_actividad'].strftime('%d %b')
                else:
                    chat['fecha_relativa'] = ""
                
                # 2. Formatear Foto de Perfil
                if chat.get('foto_filename'):
                    chat['foto_perfil'] = '/static/uploads/usuarios/' + chat['foto_filename']
                else:
                    chat['foto_perfil'] = '/static/img/default_user.png'
                
                # Limpiar campos temporales para el JSON final
                del chat['ultima_actividad']
                if 'foto_filename' in chat: del chat['foto_filename']

            resp = jsonify({'success': True, 'mensajes': chats})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e:
        print(f"Error en mensajes_recientes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@mensajes_bp.route('/unread-count')
@login_activo_requerido
def mensajes_unread_count():
    """Retorna el conteo total de mensajes no leídos."""
    user_id = session.get('usuario_id')
    if not user_id: return jsonify({'success': False, 'count': 0}), 401
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM mensajes m
                JOIN conversaciones c ON m.id_conversacion = c.id
                WHERE m.id_remitente != %s AND m.leido = false
                  AND (c.id_comprador = %s OR c.id_vendedor = %s)
            """, (user_id, user_id, user_id))
            
            count = cursor.fetchone()['total']
            resp = jsonify({'success': True, 'count': count})
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
    except Exception as e:
        print(f"Error en unread-count: {e}")
        return jsonify({'success': False, 'count': 0})
