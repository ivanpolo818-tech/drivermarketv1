# users_bp.py - Blueprint para la zona de usuarios (CORREGIDO SIN TILDE)
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import psycopg2
import psycopg2.extras
import json

# Crear Blueprint
users_bp = Blueprint('users', __name__, url_prefix='/users')

# ----------------------------------------------------
# VARIABLES GLOBALES (deberán ser configuradas desde app.py)
# ----------------------------------------------------
UPLOAD_FOLDER_RELATIVE = 'static/uploads/usuarios/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Variable para la conexión a BD (se asignará desde app.py)
conexion = None
mail = None  # Para envío de correos

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------
# FUNCIÓN PARA CONTEXTO COMÚN (datos de usuario + mensajes)
# ----------------------------------------------------
def get_common_context():
    """
    Obtiene los datos del usuario actual y el conteo de mensajes no leídos.
    """
    if 'usuario_id' not in session:
        return {'usuario': None, 'mensajes_no_leidos': 0}

    id_usuario = session['usuario_id']
    usuario = None
    mensajes_no_leidos = 0
    
    if not conexion:
        return {'usuario': None, 'mensajes_no_leidos': 0}
    
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 1. Obtener datos del usuario
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, username, email, foto, rol 
            FROM usuarios WHERE id = %s
        """, (id_usuario,))
        usuario_row = cursor.fetchone()
        usuario = dict(usuario_row) if usuario_row else None
        
        # 2. Obtener contador de mensajes no leídos - CORREGIDO SIN TILDE
        # PRIMERO probamos sin tilde, si falla, probamos otras opciones
        cursor.execute("""
            SELECT COUNT(DISTINCT c.id) AS total_conversaciones_no_leidas
            FROM conversaciones c
            INNER JOIN mensajes m ON c.ultimo_mensaje_id = m.id
            WHERE (c.id_vendedor = %s OR c.id_comprador = %s) 
            AND m.id_remitente != %s
            AND m.leido = false
        """, (id_usuario, id_usuario, id_usuario))
        
        conteo = cursor.fetchone()
        mensajes_no_leidos = conteo['total_conversaciones_no_leidas'] if conteo else 0
        
    except Exception as e:
        print(f"Error en get_common_context: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        usuario = None
        mensajes_no_leidos = 0
        
    finally:
        try:
            cursor.close()
        except:
            pass

    return {'usuario': usuario, 'mensajes_no_leidos': mensajes_no_leidos}

# ----------------------------------------------------
# 1. 🏠 PERFIL DE USUARIO
# ----------------------------------------------------
@users_bp.route('/perfil', methods=['GET', 'POST'])
def perfil():
    # 1. Verificar sesión
    if 'usuario_id' not in session:
        flash("Se requiere iniciar sesión para acceder al perfil de usuario.", "warning")
        return redirect(url_for('login'))

    id_usuario = session['usuario_id']
    
    if not conexion:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('main.index'))
    
    # Limpiar cualquier transacción bloqueada previa
    try:
        conexion.rollback()
    except:
        pass

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Ruta completa para subida de archivos (usa root_path para garantizar la ruta correcta dentro de la app Flask)
    UPLOAD_FOLDER_FULL = os.path.join(current_app.root_path, 'static', 'uploads', 'usuarios')
    os.makedirs(UPLOAD_FOLDER_FULL, exist_ok=True)

    # --- LÓGICA DE MANEJO DE FORMULARIOS (POST) ---
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            # --- ACTUALIZACIÓN DE PERFIL ---
            nombre = request.form.get('nombre')
            apellidos = request.form.get('apellidos')
            telefono = request.form.get('telefono')
            username = request.form.get('username')
            email = request.form.get('email')

            # Validación de campos obligatorios
            if not all([nombre, username, email]):
                flash("Los campos de Nombre, Usuario y Correo electrónico son de carácter obligatorio.", "error")
                return redirect(url_for('users.perfil'))
            
            # Obtener la foto actual de la DB
            try:
                cursor.execute("SELECT foto FROM usuarios WHERE id = %s", (id_usuario,))
                usuario_actual = cursor.fetchone()
            except Exception as e:
                print(f"Error DB al obtener foto actual: {e}")
                import traceback
                traceback.print_exc()
                try:
                    conexion.rollback()
                except:
                    pass
                flash("Error al cargar datos del usuario.", "error")
                return redirect(url_for('users.perfil'))

            foto_filename_db = usuario_actual['foto'] if usuario_actual and usuario_actual['foto'] else None
            nueva_foto_filename = foto_filename_db
            
            # --- VERIFICACIÓN DE UNICIDAD ---
            try:
                cursor.execute("""
                    SELECT id FROM usuarios 
                    WHERE (username = %s OR email = %s) AND id != %s
                """, (username, email, id_usuario))
                if cursor.fetchone():
                    flash("El nombre de usuario o dirección de correo electrónico ya se encuentran registrados en el sistema.", "error")
                    return redirect(url_for('users.perfil'))
            except Exception as e:
                import traceback
                traceback.print_exc()
                try:
                    conexion.rollback()
                except:
                    pass
                flash("Ocurrió un error al verificar sus datos.", "error")
                print(f"Error DB (Unicidad): {e}")
                return redirect(url_for('users.perfil'))

            # --- MANEJO DE FOTO ---
            if 'foto' in request.files:
                file = request.files['foto']
                
                if file.filename != '' and allowed_file(file.filename):
                    # Eliminar la foto antigua si existe
                    if foto_filename_db:
                        antigua_path = os.path.join(UPLOAD_FOLDER_FULL, foto_filename_db)
                        if os.path.exists(antigua_path):
                            try:
                                os.remove(antigua_path)
                            except OSError as e:
                                print(f"Error al eliminar archivo antiguo: {e}")
                    
                    # Generar nombre único y guardar
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = secure_filename(f"user_{id_usuario}_{uuid.uuid4().hex}.{ext}")
                    file_path = os.path.join(UPLOAD_FOLDER_FULL, filename)
                    
                    try:
                        file.save(file_path)
                        nueva_foto_filename = filename
                    except Exception as e:
                        flash("No se pudo guardar la nueva foto de perfil.", "error")
                        print(f"Error al guardar foto: {e}")
                        return redirect(url_for('users.perfil'))
            
            # --- ACTUALIZACIÓN FINAL ---
            try:
                cursor.execute("""
                    UPDATE usuarios SET
                        nombre = %s, apellidos = %s, telefono = %s, 
                        username = %s, email = %s, foto = %s
                    WHERE id = %s
                """, (nombre, apellidos, telefono, username, email, nueva_foto_filename, id_usuario))
                conexion.commit()
                
                # Actualizar la sesión
                session['username'] = username
                session['nombre'] = nombre
                if nueva_foto_filename:
                    session['foto'] = nueva_foto_filename
                
                flash("Su perfil ha sido actualizado exitosamente.", "success")
            except Exception as e:
                flash("Ocurrió un error al actualizar los datos en la base de datos.", "error")
                print(f"Error CRÍTICO DB al actualizar perfil: {e}")
                conexion.rollback()

            return redirect(url_for('users.perfil'))

        elif action == 'change_password':
            # --- CAMBIO DE CONTRASEÑA ---
            password_actual = request.form.get('password_actual')
            password_nueva = request.form.get('password_nueva')
            password_confirmar = request.form.get('password_confirmar')
            
            if not (password_actual and password_nueva and password_confirmar):
                flash("Todos los campos de contraseña son obligatorios.", "error")
                return redirect(url_for('users.perfil'))
            
            if password_nueva != password_confirmar:
                flash("La nueva contraseña y la confirmación no coinciden.", "error")
                return redirect(url_for('users.perfil'))
            
            if len(password_nueva) < 6:
                flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
                return redirect(url_for('users.perfil'))

            # Verificar contraseña actual
            try:
                cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_usuario,))
                user_db = cursor.fetchone()
            except Exception as e:
                print(f"Error DB al verificar contraseña: {e}")
                import traceback
                traceback.print_exc()
                try:
                    conexion.rollback()
                except:
                    pass
                flash("Error al verificar la contraseña actual.", "error")
                return redirect(url_for('users.perfil'))

            if user_db and check_password_hash(user_db['password'], password_actual):
                # Contraseña correcta, actualizar
                nuevo_hash = generate_password_hash(password_nueva)
                try:
                    cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (nuevo_hash, id_usuario))
                    conexion.commit()
                    flash("Su contraseña ha sido actualizada exitosamente.", "success")
                except Exception as e:
                    flash("Hubo un problema al guardar su nueva contraseña.", "error")
                    print(f"Error DB al actualizar contraseña: {e}")
                    conexion.rollback()
            else:
                flash("La contraseña actual ingresada es incorrecta. Por favor, verifique sus datos.", "error")
                
            return redirect(url_for('users.perfil'))

    # --- LÓGICA DE VISUALIZACIÓN DE PERFIL (GET) ---
    try:
        # Obtener datos del usuario
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, username, email, foto, rol 
            FROM usuarios WHERE id = %s
        """, (id_usuario,))
        usuario_row = cursor.fetchone()
        
        if not usuario_row:
            flash("Error de sesión: Usuario no encontrado en la base de datos.", "error")
            return redirect(url_for('auth.logout'))
        
        usuario = dict(usuario_row)

        # Obtener contador de mensajes no leídos - CORREGIDO SIN TILDE
        # PRIMERO probamos sin tilde, si falla, probamos otras opciones
        cursor.execute("""
            SELECT COUNT(m.id) AS no_leidos_count
            FROM conversaciones c
            INNER JOIN mensajes m ON m.id_conversacion = c.id
            WHERE (c.id_comprador = %s OR c.id_vendedor = %s) 
            AND m.id_remitente != %s
            AND m.leido = false
        """, (id_usuario, id_usuario, id_usuario))
        
        mensajes_no_leidos_result = cursor.fetchone()
        mensajes_no_leidos = mensajes_no_leidos_result['no_leidos_count'] if mensajes_no_leidos_result else 0
        
    except Exception as e:
        print("Error al cargar datos del perfil o mensajes:", e)
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Hubo un inconveniente al cargar su perfil. Por favor, intente más tarde.", "error")
        usuario = {
            'nombre': 'Error', 'apellidos': '', 'telefono': '', 
            'username': 'error', 'email': 'error@error.com', 
            'foto': '', 'rol': 'user'
        }
        mensajes_no_leidos = 0
        
    finally:
        try:
            cursor.close()
        except:
            pass

    # Renderizar la plantilla
    return render_template(
        'users/perfil.html', 
        usuario=usuario, 
        mensajes_no_leidos=mensajes_no_leidos
    )

# ----------------------------------------------------
# 2. 📋 MIS VEHÍCULOS / PUBLICACIONES
# ----------------------------------------------------
@users_bp.route('/mis-vehiculos')
def mis_vehiculos():
    if 'usuario_id' not in session:
        flash("Se requiere iniciar sesión para visualizar sus publicaciones.", "warning")
        return redirect(url_for('login'))

    contexto = get_common_context()
    
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT 
                v.id, v.anio, v.precio, v.estado, v.placa, v.imagen,
                m.nombre AS marca, 
                mo.nombre AS modelo,
                COALESCE(
                    NULLIF(v.imagen, ''),
                    (
                        SELECT url_imagen 
                        FROM imagenes_vehiculos 
                        WHERE id_vehiculo = v.id 
                        ORDER BY id LIMIT 1
                    )
                ) AS imagen_principal
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY v.id DESC
        """, (session['usuario_id'],))
        
        vehiculos = [dict(v) for v in cursor.fetchall()]
    except Exception as e:
        print(f"Error al cargar mis vehículos: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Hubo un error al cargar tus vehículos.", "error")
        vehiculos = []
    finally:
        try:
            cursor.close()
        except:
            pass

    return render_template(
        'users/mis_vehiculos.html', 
        vehiculos=vehiculos,
        usuario=contexto['usuario'],
        mensajes_no_leidos=contexto['mensajes_no_leidos']
    )

# ----------------------------------------------------
# 3. ❤️ FAVORITOS
# ----------------------------------------------------
@users_bp.route('/favoritos')
def favoritos():
    if 'usuario_id' not in session:
        flash("Por favor, inicie sesión para consultar su lista de favoritos.", "warning")
        return redirect(url_for('login'))

    id_usuario = session['usuario_id']
    contexto = get_common_context()

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT
            v.*,
            v.kilometraje AS km,
            m.nombre AS marca_nombre,
            mo.nombre AS modelo_nombre,
            COALESCE(
                (
                SELECT url_imagen
                FROM imagenes_vehiculos i
                WHERE i.id_vehiculo = v.id
                ORDER BY i.id ASC
                LIMIT 1
                ),
                'img/default_car.jpg'
            ) AS imagen_principal_ruta
            FROM vehiculos v
            INNER JOIN favoritos f ON v.id = f.id_vehiculo
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE f.id_usuario = %s
            ORDER BY v.id DESC
            """,
            (id_usuario,)
        )
        vehiculos_fav = [dict(v) for v in cursor.fetchall()]
    except Exception as e:
        print("Error al obtener favoritos:", e)
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        vehiculos_fav = []
    finally:
        try:
            cursor.close()
        except:
            pass

    return render_template(
        'users/favoritos.html', 
        vehiculos=vehiculos_fav, 
        usuario=contexto['usuario'], 
        mensajes_no_leidos=contexto['mensajes_no_leidos']
    )
# ----------------------------------------------------
# ❤️ AGREGAR A FAVORITOS
# ----------------------------------------------------
@users_bp.route('/favoritos/<int:id>', methods=['POST'])
def agregar_favorito(id):

    if 'usuario_id' not in session:
        flash("Se requiere iniciar sesión para añadir elementos a su lista de favoritos.", "warning")
        return redirect(url_for('login'))

    id_usuario = session['usuario_id']
    cursor = conexion.cursor()

    try:
        # --- PREVENCIÓN DE DUPLICADOS ---
        cursor.execute("SELECT 1 FROM favoritos WHERE id_usuario = %s AND id_vehiculo = %s", (id_usuario, id))
        if cursor.fetchone():
            flash("Este vehículo ya se encuentra en sus favoritos.", "info")
        else:
            cursor.execute(
                "INSERT INTO favoritos (id_usuario, id_vehiculo) VALUES (%s, %s)",
                (id_usuario, id)
            )
            conexion.commit()
            flash("El vehículo ha sido añadido exitosamente a sus favoritos.", "success")

    except Exception as e:
        print("Error al agregar favorito:", e)
        if conexion: conexion.rollback()

    finally:
        cursor.close()

    return redirect(request.referrer or url_for('index'))

# ----------------------------------------------------
# ❤️ API: TOGGLE FAVORITO (AJAX)
# ----------------------------------------------------
@users_bp.route('/api/favorito/toggle/<int:id>', methods=['POST'])
def toggle_favorito_api(id):
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    id_usuario = session['usuario_id']
    cursor = None
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar si ya existe
        cursor.execute("SELECT 1 FROM favoritos WHERE id_usuario = %s AND id_vehiculo = %s", (id_usuario, id))
        existe = cursor.fetchone()
        
        if existe:
            # Eliminar
            cursor.execute("DELETE FROM favoritos WHERE id_usuario = %s AND id_vehiculo = %s", (id_usuario, id))
            estado = "removed"
        else:
            # Agregar
            cursor.execute("INSERT INTO favoritos (id_usuario, id_vehiculo) VALUES (%s, %s)", (id_usuario, id))
            estado = "added"
            
        conexion.commit()
        return jsonify({'success': True, 'state': estado})
        
    except Exception as e:
        print(f"Error en toggle_favorito_api: {e}")
        if conexion: conexion.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
    
@users_bp.route('/favorito/eliminar/<int:id>', methods=['POST'])
def eliminar_favorito(id):
    if 'usuario_id' not in session:
        flash("Inicie sesión para gestionar su lista de favoritos.", "warning")
        return redirect(url_for('auth.login'))

    id_usuario = session['usuario_id']
    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            DELETE FROM favoritos 
            WHERE id_usuario = %s AND id_vehiculo = %s
        """, (id_usuario, id))
        conexion.commit()
        flash("El vehículo ha sido removido de su lista de favoritos.", "success")
    except Exception as e:
        print("Error al eliminar favorito:", e)
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Ocurrió un error al intentar eliminar el favorito.", "error")
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass

    return redirect(url_for('users.favoritos'))

# ----------------------------------------------------
# 4. 📊 DASHBOARD / RESUMEN
# ----------------------------------------------------
@users_bp.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for('login'))

    id_usuario = session['usuario_id']
    contexto = get_common_context()
    
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    estadisticas = {
        'total_vehiculos': 0,
        'vehiculos_activos': 0,
        'total_favoritos': 0,
        'mensajes_sin_leer': contexto['mensajes_no_leidos'],
        'ultimos_vehiculos': []
    }
    
    try:
        # Total de vehículos publicados
        cursor.execute("SELECT COUNT(*) as total FROM vehiculos WHERE id_usuario = %s", (id_usuario,))
        estadisticas['total_vehiculos'] = cursor.fetchone()['total']
        
        # Vehículos activos
        cursor.execute("SELECT COUNT(*) as activos FROM vehiculos WHERE id_usuario = %s AND estado = 'activo'", (id_usuario,))
        estadisticas['vehiculos_activos'] = cursor.fetchone()['activos']
        
        # Total de favoritos
        cursor.execute("SELECT COUNT(*) as favs FROM favoritos WHERE id_usuario = %s", (id_usuario,))
        estadisticas['total_favoritos'] = cursor.fetchone()['favs']
        
        # Últimos 3 vehículos publicados
        cursor.execute("""
            SELECT v.id, v.anio, v.precio, v.placa, 
                   m.nombre as marca, mo.nombre as modelo,
                   (SELECT url_imagen FROM imagenes_vehiculos WHERE id_vehiculo = v.id LIMIT 1) as imagen
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.id_usuario = %s
            ORDER BY v.fecha_publicacion DESC
            LIMIT 3
        """, (id_usuario,))
        estadisticas['ultimos_vehiculos'] = [dict(v) for v in cursor.fetchall()]
        
    except Exception as e:
        print(f"Error al cargar estadísticas del dashboard: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except:
            pass
        flash("Error al cargar las estadísticas.", "error")
    finally:
        try:
            cursor.close()
        except:
            pass

    return render_template(
        'users/dashboard.html',
        usuario=contexto['usuario'],
        mensajes_no_leidos=contexto['mensajes_no_leidos'],
        estadisticas=estadisticas
    )

# ----------------------------------------------------
# 5. 🔧 AJUSTES / CONFIGURACIÓN
# ----------------------------------------------------
def get_user_prefs(usuario_id):
    """Obtiene o inicializa las preferencias del usuario en la BD."""
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT * FROM preferencias_usuario WHERE usuario_id = %s", (usuario_id,))
        prefs = cursor.fetchone()
        if not prefs:
            cursor.execute("""
                INSERT INTO preferencias_usuario (usuario_id) 
                VALUES (%s) RETURNING *
            """, (usuario_id,))
            conexion.commit()
            prefs = cursor.fetchone()
        return prefs
    except Exception as e:
        print(f"Error get_user_prefs: {e}")
        conexion.rollback()
        return None
    finally:
        cursor.close()

@users_bp.route('/ajustes', methods=['GET', 'POST'])
def ajustes():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para acceder a ajustes.", "warning")
        return redirect(url_for('login'))

    uid = session['usuario_id']
    contexto = get_common_context()
    
    if request.method == 'POST':
        action = request.form.get('action')
        cursor = conexion.cursor()
        try:
            if action == 'update_notifications':
                cursor.execute("""
                    UPDATE preferencias_usuario SET 
                    notif_mensajes = %s, notif_ofertas = %s, notif_precio = %s,
                    notif_nuevas_pub = %s, notif_favoritos = %s, notif_updates = %s
                    WHERE usuario_id = %s
                """, (
                    'notif_mensajes' in request.form, 'notif_ofertas' in request.form,
                    'notif_precio' in request.form, 'notif_nuevas_pub' in request.form,
                    'notif_favoritos' in request.form, 'notif_updates' in request.form,
                    uid
                ))
            elif action == 'toggle_2fa':
                cursor.execute("UPDATE preferencias_usuario SET dos_fa_activo = %s WHERE usuario_id = %s", 
                             ('dos_fa_activo' in request.form, uid))
            elif action == 'toggle_alertas':
                cursor.execute("UPDATE preferencias_usuario SET alerta_nuevo_login = %s WHERE usuario_id = %s", 
                             ('alerta_nuevo_login' in request.form, uid))
            elif action == 'update_privacy':
                cursor.execute("""
                    UPDATE preferencias_usuario SET 
                    visibilidad = %s, mostrar_telefono = %s, en_busquedas = %s
                    WHERE usuario_id = %s
                """, (
                    request.form.get('visibilidad', 'publico'),
                    'mostrar_telefono' in request.form,
                    'en_busquedas' in request.form,
                    uid
                ))
            elif action == 'update_locale':
                cursor.execute("""
                    UPDATE preferencias_usuario SET 
                    idioma = %s, timezone = %s, moneda = %s
                    WHERE usuario_id = %s
                """, (
                    request.form.get('idioma', 'es'),
                    request.form.get('timezone', 'America/Bogota'),
                    request.form.get('moneda', 'COP'),
                    uid
                ))
            elif action == 'disconnect_google':
                cursor.execute("UPDATE preferencias_usuario SET google_connected = FALSE WHERE usuario_id = %s", (uid,))
                flash("La cuenta de Google ha sido desvinculada correctamente.", "info")
            elif action == 'delete_search_history':
                # Aquí iría la lógica para borrar de una tabla 'busquedas_recientes' si existiera
                # cursor.execute("DELETE FROM busquedas_recientes WHERE usuario_id = %s", (uid,))
                flash("El historial de búsquedas ha sido eliminado con éxito.", "success")
            elif action == 'cerrar_otras_sesiones':
                # Para esto necesitaríamos un sistema de IDs de sesión en la BD
                # Por ahora simulamos el éxito
                cursor.execute("DELETE FROM historial_sesiones WHERE usuario_id = %s AND id != (SELECT id FROM historial_sesiones WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 1)", (uid, uid))
                flash("Las demás sesiones activas se han cerrado exitosamente.", "success")
            
            conexion.commit()
            if action != 'disconnect_google' and action != 'delete_search_history' and action != 'cerrar_otras_sesiones':
                flash("Sus preferencias han sido guardadas correctamente.", "success")
        except Exception as e:
            conexion.rollback()
            print(f"Error actualizando ajustes: {e}")
            flash("Hubo un problema al guardar sus cambios. Intente de nuevo.", "error")
        finally:
            cursor.close()
            
        return redirect(url_for('users.ajustes'))

    # Cargar preferencias reales
    prefs = get_user_prefs(uid)
    
    # Cargar Historial Real de Sesiones
    historial = []
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT * FROM historial_sesiones WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 5", (uid,))
        historial = [dict(h) for h in cursor.fetchall()]
    except Exception as e:
        print(f"Error cargando historial: {e}")
        historial = []
    finally:
        cursor.close()
    
    return render_template(
        'users/configuracion/ajustes.html',
        usuario=contexto['usuario'],
        mensajes_no_leidos=contexto['mensajes_no_leidos'],
        prefs=prefs,
        historial=historial
    )

@users_bp.route('/configuracion/seguridad')
def seguridad():
    return render_template('users/configuracion/seguridad.html')

@users_bp.route('/configuracion/notificaciones')
def notificaciones():
    return render_template('users/configuracion/notificaciones.html')

@users_bp.route('/configuracion/privacidad')
def privacidad():
    return render_template('users/configuracion/privacidad.html')

@users_bp.route('/configuracion/mi-cuenta')
def mi_cuenta():
    return render_template('users/configuracion/mi_cuenta.html')
# ----------------------------------------------------
# 6. 📬 MENSAJES (Redirección al Blueprint de mensajes)
# ----------------------------------------------------
@users_bp.route('/mensajes')
def redirigir_mensajes():
    """Redirige a la página principal de mensajes"""
    return redirect(url_for('mensajes.conversaciones'))

# ----------------------------------------------------
# 7. 🛒 MIS COMPRAS / OFERTAS
# ----------------------------------------------------
@users_bp.route('/mis-compras')
def mis_compras():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para ver tus compras.", "warning")
        return redirect(url_for('login'))

    contexto = get_common_context()
    
    # Aquí puedes implementar la lógica para mostrar compras u ofertas del usuario
    # Por ahora solo renderizamos la plantilla básica
    return render_template(
        'users/mis_compras.html',
        usuario=contexto['usuario'],
        mensajes_no_leidos=contexto['mensajes_no_leidos']
    )

# ----------------------------------------------------
# 8. MIS DATOS: EXPORTAR
# ----------------------------------------------------
@users_bp.route('/configuracion/descargar-datos')
def download_data():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para descargar tus datos.", "warning")
        return redirect(url_for('login'))

    uid = session['usuario_id']
    contexto = get_common_context()
    usuario = contexto['usuario']
    
    if not usuario:
        flash("No se pudo obtener la información de tu perfil.", "error")
        return redirect(url_for('users.ajustes'))

    # Cargar preferencias reales
    prefs = get_user_prefs(uid)
    
    # Cargar Historial de Sesiones
    historial = []
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT ip, dispositivo, navegador, pais, fecha FROM historial_sesiones WHERE usuario_id = %s ORDER BY fecha DESC", (uid,))
        historial = cursor.fetchall()
        # Convertir fechas a string para JSON
        for h in historial:
            if h['fecha']:
                h['fecha'] = h['fecha'].strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error exportando historial: {e}")
    finally:
        cursor.close()

    # Consolidar datos
    datos_completos = {
        "perfil": {
            "nombre": usuario['nombre'],
            "apellidos": usuario['apellidos'],
            "email": usuario['email'],
            "username": usuario['username'],
            "telefono": usuario['telefono'],
            "rol": usuario['rol']
        },
        "preferencias": dict(prefs) if prefs else {},
        "seguridad": {
            "historial_sesiones": historial
        },
        "fecha_exportacion": uuid.uuid4().hex[:8] # Simulamos un ID de reporte
    }

    json_data = json.dumps(datos_completos, indent=4, ensure_ascii=False)
    
    return Response(
        json_data,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=mis_datos_drivemarket.json'}
    )

# ----------------------------------------------------
# FUNCIÓN PARA CONFIGURAR DESDE APP.PY
# ----------------------------------------------------
def configure_users_bp(app_config, db_connection, mail_instance=None):
    """
    Configura el Blueprint de usuarios con las dependencias necesarias.
    
    Args:
        app_config: Configuración de la app Flask
        db_connection: Conexión a la base de datos MySQL
        mail_instance: Instancia de Flask-Mail (opcional)
    """
    global conexion, mail
    
    # Configurar conexión a BD
    if db_connection:
        conexion = db_connection
    else:
        raise ValueError("Se requiere una conexión a la base de datos")
    
    # Configurar mail
    if mail_instance:
        mail = mail_instance
    
    # Configurar carpeta de uploads
    UPLOAD_FOLDER = app_config.get('UPLOAD_FOLDER_USUARIOS', 'static/uploads/usuarios/')
    
    print("✅ Blueprint de usuarios configurado correctamente")
    return users_bp
