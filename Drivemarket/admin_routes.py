from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from flask import current_app
import uuid
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# --- IMPORTACIONES PARA CORREO ---
import requests, subprocess
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

load_dotenv()

# --- CONFIGURACIÓN DEL SERVIDOR DE CORREO ---
SMTP_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("MAIL_PORT", "587"))
SENDER_EMAIL = os.getenv("MAIL_USERNAME", "adsotareas@gmail.com")
SENDER_PASSWORD = os.getenv("MAIL_PASSWORD", "hyvc ztcv ploj vfzd")

from helpers.email_templates import generar_html_email

def enviar_notificacion_email(destinatario, asunto, mensaje_html):
    """
    Envía correo usando la configuración existente de Flask-Mail.
    El mensaje_html ya debe venir procesado por el generador de plantillas.
    """
    try:
        from flask_mail import Message
        from app import mail
        
        if not mail:
            print("[ERROR] Flask-Mail no está inicializado")
            return False
        
        msg = Message(
            subject=asunto,
            sender=("Drive Market", "adsotareas@gmail.com"),
            recipients=[destinatario]
        )
        msg.html = mensaje_html
        print(f"[SUCCESS] Correo enviado exitosamente a: {destinatario}")
        return True
        
    except Exception as e:
        print(f"[ERROR] enviando correo: {str(e)}")
        return False
    
# --- CONFIGURACIÓN DE IMÁGENES ---
UPLOAD_FOLDER = 'static/uploads/vehiculos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def guardar_imagen_vehiculo(archivo):
    """Guarda una imagen y retorna el nombre del archivo"""
    print(f"🟢 DENTRO DE guardar_imagen_vehiculo")
    
    if not archivo:
        print("🟢 archivo es None, retornando None")
        return None
        
    if not archivo.filename:
        print("🟢 archivo sin filename, retornando None")
        return None
    
    print(f"🟢 filename original: {archivo.filename}")
    
    if not allowed_file(archivo.filename):
        print(f"🟢 archivo no permitido: {archivo.filename}")
        raise Exception("Tipo de archivo no permitido. Solo: png, jpg, jpeg, gif, webp")
    
    try:
        filename = secure_filename(archivo.filename)
        print(f"🟢 secure_filename: {filename}")
        
        unique_filename = f"vehiculo_{uuid.uuid4().hex[:8]}_{filename}"
        
        ruta_completa = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        
        os.makedirs(ruta_completa, exist_ok=True)
        
        ruta_archivo = os.path.join(ruta_completa, unique_filename)
        
        archivo.save(ruta_archivo)
        print(f"[INFO] Imagen guardada: {unique_filename}")
        
        return f"uploads/vehiculos/{unique_filename}"
        
    except Exception as e:
        print(f"[ERROR] guardando imagen: {e}")
        import traceback
        traceback.print_exc()
        raise

def eliminar_imagen_vehiculo(nombre_archivo):
    """Elimina una imagen del servidor"""
    
    if not nombre_archivo or nombre_archivo == 'default.jpg':
        return
    
    try:
        ruta_completa = os.path.join(current_app.root_path, UPLOAD_FOLDER, nombre_archivo)
        
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
            print(f"[INFO] Imagen eliminada: {nombre_archivo}")
        else:
            print(f"[WARNING] Archivo no existe: {ruta_completa}")
            
    except Exception as e:
        print(f"[ERROR] eliminando imagen: {e}")
    
# La conexión se inyectará desde app.py
conexion = None

# Crear blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.context_processor
def inject_admin_alerts():
    alertas = {'vendedores': 0, 'reportes': 0, 'total': 0}
    notificaciones = []
    try:
        from flask import current_app
        # Usamos la conexión global
        if conexion and not conexion.closed:
            cur = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Vendedores pendientes
            cur.execute("SELECT COUNT(*) as c FROM perfil_vendedor WHERE estado_verificacion = 'pendiente'")
            row = cur.fetchone()
            alertas['vendedores'] = row['c'] if row else 0
            
            # 2. Reportes pendientes
            cur.execute("SELECT COUNT(*) as c FROM reportes WHERE estado = 'Pendiente' OR estado = 'pendiente'")
            row2 = cur.fetchone()
            alertas['reportes'] = row2['c'] if row2 else 0
            
            alertas['total'] = alertas['vendedores'] + alertas['reportes']
            
            # 3. Componente de Notificaciones (Top bar)
            # Traemos 3 últimos usuarios
            cur.execute("SELECT id, email, fecha_registro FROM usuarios ORDER BY id DESC LIMIT 3")
            for u in cur.fetchall():
                notificaciones.append({
                    'icon': 'fa-user-plus', 'color': '#10b981', 'titulo': 'Nuevo usuario',
                    'texto': f"{u['email']} se registró", 'fecha': u['fecha_registro']
                })
                
            # Traemos 3 últimos vehículos
            cur.execute("""
                SELECT v.id, m.nombre as marca, mo.nombre as modelo, v.fecha_publicacion 
                FROM vehiculos v LEFT JOIN marcas m ON v.id_marca = m.id LEFT JOIN modelos mo ON v.id_modelo = mo.id 
                WHERE v.fecha_publicacion IS NOT NULL ORDER BY v.id DESC LIMIT 3
            """)
            for v in cur.fetchall():
                notificaciones.append({
                    'icon': 'fa-car', 'color': '#ff7043', 'titulo': 'Nuevo vehículo',
                    'texto': f"{v['marca'] or 'Auto'} {v['modelo'] or ''} publicado", 'fecha': v['fecha_publicacion']
                })
                
            # Traemos 3 últimos reportes
            cur.execute("SELECT id, motivo, fecha_reporte FROM reportes ORDER BY id DESC LIMIT 3")
            for r in cur.fetchall():
                notificaciones.append({
                    'icon': 'fa-exclamation-triangle', 'color': '#ef4444', 'titulo': 'Nuevo reporte',
                    'texto': f"{r['motivo']}", 'fecha': r['fecha_reporte']
                })
            
            # Ordenar todas por fecha y quedarnos con las 5 más recientes
            notificaciones.sort(key=lambda x: x['fecha'], reverse=True)
            notificaciones = notificaciones[:5]
            
            cur.close()
    except Exception as e:
        print(f"Error en context_processor de alertas: {e}")
        
    return dict(alertas_globales=alertas, notificaciones_recientes=notificaciones)

# ----------------------------------------------------
# HELPER DE AUDITORÍA
# ----------------------------------------------------
def registrar_log(accion, entidad=None, id_entidad=None, descripcion=None):
    """Registra una acción del administrador en la tabla logs_admin."""
    try:
        cur = conexion.cursor()
        id_admin = session.get('usuario_id')
        nombre_admin = session.get('nombre', 'Desconocido')
        ip = request.remote_addr
        cur.execute("""
            INSERT INTO logs_admin (id_admin, nombre_admin, accion, entidad, id_entidad, descripcion, ip, fecha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (id_admin, nombre_admin, accion, entidad, id_entidad, descripcion, ip))
        conexion.commit()
        cur.close()
    except Exception as e:
        print(f"[LOG ERROR] No se pudo registrar el log: {e}")

# ----------------------------------------------------
# DECORADORES
# ----------------------------------------------------
def login_activo_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Se requiere iniciar sesión para acceder al panel administrativo.", "warning")
            return redirect(url_for('login'))

        estado_usuario = session.get('estado')
        
        if estado_usuario == 'inactivo':
            session.clear()
            flash("Su cuenta se encuentra inactiva. Contacte al administrador del sistema.", "danger")
            return redirect(url_for('login'))
        
        if estado_usuario == 'bloqueado':
            session.clear()
            flash("Su cuenta ha sido bloqueada por motivos de seguridad.", "danger")
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorador

def admin_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if session.get('rol') not in ['admin', 'superadmin', 'editor', 'moderador']:
            flash("Acceso denegado. No posee los privilegios suficientes para acceder a esta sección.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorador

def requiere_roles(* roles_permitidos):
    def wrapper(f):
        @wraps(f)
        def decorador(*args, **kwargs):
            rol_actual = session.get('rol')
            if rol_actual not in roles_permitidos and rol_actual not in ['admin', 'superadmin']:
                flash("Nivel de acceso insuficiente para realizar esta operación.", "danger")
                return redirect(url_for('admin.admin_dashboard'))
            return f(*args, **kwargs)
        return decorador
    return wrapper

# ---------------------------------------------------------------
#  GESTIÓN DE CATEGORÍAS (Marcas y Tipos)
# ---------------------------------------------------------------
@admin_bp.route('/categorias')
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def administrar_categorias():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Marcas (incluyendo logo y destacado)
    cursor.execute("""
        SELECT m.id, m.nombre, m.logo, m.destacada, COUNT(v.id) as total_vehiculos 
        FROM marcas m 
        LEFT JOIN vehiculos v ON m.id = v.id_marca 
        GROUP BY m.id, m.nombre, m.logo, m.destacada 
        ORDER BY m.nombre ASC
    """)
    marcas = cursor.fetchall()
    
    # Tipos
    cursor.execute("""
        SELECT t.id, t.nombre, COUNT(v.id) as total_vehiculos 
        FROM tipos_vehiculos t 
        LEFT JOIN vehiculos v ON t.id = v.id_tipo 
        GROUP BY t.id ORDER BY t.nombre ASC
    """)
    tipos = cursor.fetchall()
    cursor.close()
    return render_template('admin/admin_categorias.html', marcas=marcas, tipos=tipos)

@admin_bp.route('/categorias/<entidad>/crear', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def crear_categoria(entidad):
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash("El campo de nombre es obligatorio.", "danger")
        return redirect(url_for('admin.administrar_categorias'))
    
    tabla = 'marcas' if entidad == 'marca' else 'tipos_vehiculos'
    try:
        cur = conexion.cursor()
        if entidad == 'marca':
            destacada = request.form.get('destacada') == 'on'
            logo_nombre = None
            
            # Manejo de logo
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename:
                    # Guardar en static/img/logos/
                    filename = secure_filename(file.filename)
                    unique_filename = f"logo_{uuid.uuid4().hex[:8]}_{filename}"
                    ruta_logos = os.path.join(current_app.root_path, 'static', 'img', 'logos')
                    os.makedirs(ruta_logos, exist_ok=True)
                    file.save(os.path.join(ruta_logos, unique_filename))
                    logo_nombre = unique_filename

            cur.execute("INSERT INTO marcas (nombre, logo, destacada) VALUES (%s, %s, %s) RETURNING id", 
                       (nombre, logo_nombre, destacada))
        else:
            cur.execute("INSERT INTO tipos_vehiculos (nombre) VALUES (%s) RETURNING id", (nombre,))
            
        nuevo_id = cur.fetchone()[0]
        conexion.commit()
        cur.close()
        registrar_log('crear_'+entidad, tabla, nuevo_id, f"Nombre: {nombre}")
        flash(f"Se ha creado exitosamente el registro de {entidad}.", "success")
    except Exception as e:
        conexion.rollback()
        flash(f"Error al crear: {e}", "danger")
    return redirect(url_for('admin.administrar_categorias'))

@admin_bp.route('/categorias/<entidad>/<int:id>/editar', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def editar_categoria(entidad, id):
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash("El nombre proporcionado no es válido.", "danger")
        return redirect(url_for('admin.administrar_categorias'))
    
    tabla = 'marcas' if entidad == 'marca' else 'tipos_vehiculos'
    try:
        cur = conexion.cursor()
        if entidad == 'marca':
            destacada = request.form.get('destacada') == 'on'
            
            # Manejo de logo
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_filename = f"logo_{uuid.uuid4().hex[:8]}_{filename}"
                    ruta_logos = os.path.join(current_app.root_path, 'static', 'img', 'logos')
                    os.makedirs(ruta_logos, exist_ok=True)
                    file.save(os.path.join(ruta_logos, unique_filename))
                    
                    # Actualizar con logo
                    cur.execute("UPDATE marcas SET nombre = %s, logo = %s, destacada = %s WHERE id = %s", 
                               (nombre, unique_filename, destacada, id))
                else:
                    # Actualizar solo nombre y destacada
                    cur.execute("UPDATE marcas SET nombre = %s, destacada = %s WHERE id = %s", 
                               (nombre, destacada, id))
            else:
                cur.execute("UPDATE marcas SET nombre = %s, destacada = %s WHERE id = %s", 
                           (nombre, destacada, id))
        else:
            cur.execute("UPDATE tipos_vehiculos SET nombre = %s WHERE id = %s", (nombre, id))
            
        conexion.commit()
        cur.close()
        registrar_log('editar_'+entidad, tabla, id, f"Nuevo nombre: {nombre}")
        flash(f"La categoría de {entidad} ha sido actualizada exitosamente.", "success")
    except Exception as e:
        conexion.rollback()
        flash(f"Error al editar: {e}", "danger")
    return redirect(url_for('admin.administrar_categorias'))

@admin_bp.route('/categorias/<entidad>/<int:id>/eliminar', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def eliminar_categoria(entidad, id):
    tabla = 'marcas' if entidad == 'marca' else 'tipos_vehiculos'
    columna_fk = 'id_marca' if entidad == 'marca' else 'id_tipo'
    try:
        cur = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"SELECT COUNT(id) as c FROM vehiculos WHERE {columna_fk} = %s", (id,))
        count = cur.fetchone()['c']
        if count > 0:
            flash(f"Operación cancelada. Existen {count} registro(s) dependientes vinculados a esta categoría.", "warning")
            cur.close()
            return redirect(url_for('admin.administrar_categorias'))
        
        cur.execute(f"DELETE FROM {tabla} WHERE id = %s", (id,))
        conexion.commit()
        flash(f"La categoría de {entidad} ha sido eliminada del sistema.", "success")
        cur.close()
    except Exception as e:
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for('admin.administrar_categorias'))

# ---------------------------------------------------------------
#  DASHBOARD ADMINISTRATIVO
# ---------------------------------------------------------------
@admin_bp.route('/dashboard')
@login_activo_requerido
@admin_requerido
def admin_dashboard():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    import datetime

    cursor.execute("SELECT COUNT(*) AS total FROM vehiculos")
    total_vehiculos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    total_usuarios = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM favoritos")
    total_favoritos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM vehiculos WHERE DATE(fecha_publicacion) = CURRENT_DATE")
    publicados_hoy = cursor.fetchone()['total']

    # Obtener los 7 últimos vehículos
    cursor.execute("""
        SELECT v.id, v.precio, v.anio, m.nombre as marca, mo.nombre as modelo,
               (SELECT i.url_imagen FROM imagenes_vehiculos i WHERE i.id_vehiculo = v.id LIMIT 1) as imagen
        FROM vehiculos v
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        ORDER BY v.id DESC LIMIT 7
    """)
    ultimos_vehiculos = cursor.fetchall()

    # Solicitudes pendientes de verificación
    cursor.execute("SELECT COUNT(*) as pendientes FROM perfil_vendedor WHERE estado_verificacion = 'pendiente'")
    res = cursor.fetchone()
    solicitudes = res['pendientes'] if res else 0

    # Publicaciones por mes (año actual)
    cursor.execute("""
        SELECT EXTRACT(MONTH FROM fecha_publicacion) as mes, COUNT(id) as total
        FROM vehiculos
        WHERE EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY EXTRACT(MONTH FROM fecha_publicacion)
    """)
    meses_db = cursor.fetchall()
    publicaciones_meses = [0] * 12
    for row in meses_db:
        if row['mes']:
            publicaciones_meses[int(row['mes']) - 1] = row['total']

    # ── KPI VARIACIÓN MES ANTERIOR ────────────────────────────────
    cursor.execute("""
        SELECT COUNT(*) AS total FROM vehiculos
        WHERE EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE) - 1
          AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
    """)
    vehiculos_mes_ant = max((cursor.fetchone() or {}).get('total', 0), 1)

    cursor.execute("""
        SELECT COUNT(*) AS total FROM vehiculos
        WHERE EXTRACT(MONTH FROM fecha_publicacion) = EXTRACT(MONTH FROM CURRENT_DATE)
          AND EXTRACT(YEAR FROM fecha_publicacion) = EXTRACT(YEAR FROM CURRENT_DATE)
    """)
    vehiculos_mes_act = (cursor.fetchone() or {}).get('total', 0)

    cursor.execute("""
        SELECT COUNT(*) AS total FROM usuarios
        WHERE EXTRACT(MONTH FROM fecha_registro) = EXTRACT(MONTH FROM CURRENT_DATE) - 1
          AND EXTRACT(YEAR FROM fecha_registro) = EXTRACT(YEAR FROM CURRENT_DATE)
    """)
    usuarios_mes_ant = max((cursor.fetchone() or {}).get('total', 0), 1)

    cursor.execute("""
        SELECT COUNT(*) AS total FROM usuarios
        WHERE EXTRACT(MONTH FROM fecha_registro) = EXTRACT(MONTH FROM CURRENT_DATE)
          AND EXTRACT(YEAR FROM fecha_registro) = EXTRACT(YEAR FROM CURRENT_DATE)
    """)
    usuarios_mes_act = (cursor.fetchone() or {}).get('total', 0)

    def variacion_pct(actual, anterior):
        if anterior == 0:
            return 100 if actual > 0 else 0
        return round(((actual - anterior) / anterior) * 100)

    kpi_variacion = {
        'vehiculos': variacion_pct(vehiculos_mes_act, vehiculos_mes_ant),
        'usuarios': variacion_pct(usuarios_mes_act, usuarios_mes_ant),
    }

    # ── BARRAS DE PROGRESO DINÁMICAS ─────────────────────────────
    max_mes = max(publicaciones_meses) if any(publicaciones_meses) else 1
    mes_actual_idx = datetime.date.today().month - 1
    pct_vehiculos_bar = round((publicaciones_meses[mes_actual_idx] / max_mes) * 100) if max_mes > 0 else 0
    pct_usuarios_bar  = min(round((usuarios_mes_act / usuarios_mes_ant) * 100), 100)
    pct_favoritos_bar = min(round((total_favoritos / max(total_vehiculos, 1)) * 100), 100)
    pct_hoy_bar       = round((publicados_hoy / max(publicaciones_meses[mes_actual_idx], 1)) * 100) if publicaciones_meses[mes_actual_idx] > 0 else 0

    # ── ACTIVIDAD RECIENTE ────────────────────────────────────────
    actividad = []
    # 5 Vehículos recientes
    cursor.execute("""
        SELECT v.id, m.nombre as marca, mo.nombre as modelo, v.fecha_publicacion as fecha
        FROM vehiculos v
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        WHERE v.fecha_publicacion IS NOT NULL
        ORDER BY v.id DESC LIMIT 5
    """)
    for v in cursor.fetchall():
        actividad.append({
            'tipo': 'vehiculo',
            'titulo': 'Vehículo publicado',
            'descripcion': f"{v['marca'] or 'Auto'} {v['modelo'] or ''} fue agregado",
            'fecha': v['fecha']
        })
        
    # 5 Usuarios recientes
    cursor.execute("SELECT id, nombre, email, fecha_registro as fecha FROM usuarios ORDER BY id DESC LIMIT 5")
    for u in cursor.fetchall():
        actividad.append({
            'tipo': 'usuario',
            'titulo': 'Nuevo usuario',
            'descripcion': f"{u['email']} se registró",
            'fecha': u['fecha']
        })
        
    # 5 Favoritos recientes
    cursor.execute("""
        SELECT f.id, m.nombre as marca, mo.nombre as modelo, f.fecha_agregado as fecha
        FROM favoritos f
        JOIN vehiculos v ON f.id_vehiculo = v.id
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        ORDER BY f.id DESC LIMIT 5
    """)
    for f in cursor.fetchall():
        actividad.append({
            'tipo': 'favorito',
            'titulo': 'Favorito agregado',
            'descripcion': f"{f['marca'] or 'Auto'} {f['modelo'] or ''} fue guardado",
            'fecha': f['fecha']
        })
        
    # Ordenar linea de tiempo combinada
    actividad.sort(key=lambda x: x['fecha'], reverse=True)

    # Obtener el Top 5 de Marcas para el Donut Chart
    cursor.execute("""
        SELECT m.nombre as nombre, COUNT(v.id) as cantidad
        FROM vehiculos v 
        JOIN marcas m ON v.id_marca = m.id 
        GROUP BY m.nombre 
        ORDER BY cantidad DESC LIMIT 5
    """)
    top_marcas = cursor.fetchall()

    # ── NOTIFICACIONES REALES ─────────────────────────────────────
    notificaciones = []
    try:
        cursor.execute("""
            SELECT pv.nombre_tienda, pv.created_at, u.email
            FROM perfil_vendedor pv
            JOIN usuarios u ON pv.usuario_id = u.id
            WHERE pv.estado_verificacion = 'pendiente'
            ORDER BY pv.created_at DESC LIMIT 5
        """)
        for row in cursor.fetchall():
            notificaciones.append({
                'icon': 'fa-user-check', 'color': '#f59e0b',
                'titulo': 'Solicitud de verificación',
                'texto': f"{row.get('nombre_tienda') or row.get('email')} espera aprobación",
                'fecha': row.get('created_at')
            })
    except Exception:
        conexion.rollback()

    try:
        cursor.execute("""
            SELECT nombre, email, fecha_registro
            FROM usuarios
            WHERE fecha_registro >= NOW() - INTERVAL '48 hours'
            ORDER BY fecha_registro DESC LIMIT 3
        """)
        for row in cursor.fetchall():
            notificaciones.append({
                'icon': 'fa-user-plus', 'color': '#10b981',
                'titulo': 'Nuevo usuario registrado',
                'texto': f"{row['nombre']} ({row['email']})",
                'fecha': row['fecha_registro']
            })
    except Exception:
        conexion.rollback()

    if publicados_hoy > 0:
        notificaciones.append({
            'icon': 'fa-car', 'color': '#ff7043',
            'titulo': f"{publicados_hoy} vehículo(s) publicado(s) hoy",
            'texto': 'Revisa las nuevas publicaciones en el panel de vehículos',
            'fecha': datetime.datetime.now()
        })

    notificaciones.sort(key=lambda x: x['fecha'] or datetime.datetime.min, reverse=True)

    # ── DATOS DEL ADMIN LOGUEADO ──────────────────────────────────
    admin_usuario = None
    try:
        uid = session.get('usuario_id')
        if uid:
            cursor.execute("SELECT id, nombre, email, foto, rol FROM usuarios WHERE id = %s", (uid,))
            admin_usuario = cursor.fetchone()
    except Exception:
        conexion.rollback()

    cursor.close()

    return render_template(
        'admin/dashboard.html',
        total_vehiculos=total_vehiculos,
        total_usuarios=total_usuarios,
        total_favoritos=total_favoritos,
        publicados_hoy=publicados_hoy,
        ultimos=ultimos_vehiculos,
        solicitudes_pendientes=solicitudes,
        publicaciones_meses=publicaciones_meses,
        actividad_reciente=actividad,
        top_marcas=top_marcas,
        notificaciones_recientes=notificaciones,
        admin_usuario=admin_usuario,
        kpi_variacion=kpi_variacion,
        pct_vehiculos_bar=pct_vehiculos_bar,
        pct_usuarios_bar=pct_usuarios_bar,
        pct_favoritos_bar=pct_favoritos_bar,
        pct_hoy_bar=pct_hoy_bar,
    )

@admin_bp.route('/dashboard/live')
@login_activo_requerido
@admin_requerido
def admin_dashboard_live():
    """Endpoint para polling AJAX que alimenta el dashboard en tiempo real."""
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT COUNT(*) AS total FROM vehiculos")
    total_v = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    total_u = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM favoritos")
    total_f = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM vehiculos WHERE DATE(fecha_publicacion) = CURRENT_DATE")
    pub_hoy = cursor.fetchone()['total']
    cursor.close()
    
    return {
        "vehiculos": total_v,
        "usuarios": total_u,
        "favoritos": total_f,
        "hoy": pub_hoy
    }

@admin_bp.route('/dashboard/health')
@login_activo_requerido
@admin_requerido
def admin_dashboard_health():
    """Endpoint para el widget de Salud del Sistema."""
    import time

    # 1. Latencia de Base de Datos
    db_ok = False
    db_latency_ms = 0
    try:
        t0 = time.time()
        cur = conexion.cursor()
        cur.execute("SELECT 1")
        cur.close()
        db_latency_ms = round((time.time() - t0) * 1000, 1)
        db_ok = True
    except Exception:
        db_ok = False

    # 2. Estado del servicio de correo (solo verificar config)
    mail_ok = bool(SENDER_EMAIL and SENDER_PASSWORD)

    # 3. Espacio de almacenamiento en uploads
    storage_used_mb = 0
    storage_ok = True
    try:
        uploads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        if os.path.exists(uploads_path):
            total_bytes = sum(
                os.path.getsize(os.path.join(dirpath, f))
                for dirpath, _, filenames in os.walk(uploads_path)
                for f in filenames
            )
            storage_used_mb = round(total_bytes / (1024 * 1024), 1)
        storage_ok = storage_used_mb < 4500  # Alerta si supera 4.5 GB
    except Exception:
        pass

    # 4. Conexión a Internet (External Link)
    internet_ok = False
    try:
        # Petición a Cloudflare DNS, cualquier respuesta sin fallo de red marca conexión activa
        res_int = requests.get("https://1.1.1.1", timeout=2.0)
        internet_ok = True
    except Exception:
        internet_ok = False

    # 5. Uso de RAM (Nativo Windows)
    ram_usage = 0
    ram_ok = True
    try:
        import json
        cmd = ["powershell", "-Command", "Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize | ConvertTo-Json"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
        data_ram = json.loads(output)
        
        if 'FreePhysicalMemory' in data_ram and 'TotalVisibleMemorySize' in data_ram:
            total = data_ram['TotalVisibleMemorySize']
            free = data_ram['FreePhysicalMemory']
            used = total - free
            ram_usage = round((used / total) * 100, 1)
            ram_ok = ram_usage < 85 # Alerta si supera el 85%
    except Exception:
        ram_usage = "N/A"
        ram_ok = False

    return {
        "db": {"ok": db_ok, "latency_ms": db_latency_ms},
        "mail": {"ok": mail_ok},
        "storage": {"ok": storage_ok, "used_mb": storage_used_mb},
        "internet": {"ok": internet_ok},
        "ram": {"ok": ram_ok, "usage": ram_usage}
    }

@admin_bp.route('/buscar')
@login_activo_requerido
@admin_requerido
def buscar_global():
    """Endpoint unificado AJAX para buscar vehículos, usuarios y tiendas."""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return {'resultados': []}
        
    resultados = []
    try:
        from flask import current_app, url_for
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar usuarios (max 3)
        cursor.execute("""
            SELECT id, email, nombre 
            FROM usuarios 
            WHERE email LIKE %s OR nombre LIKE %s 
            LIMIT 3
        """, (f"%{q}%", f"%{q}%"))
        for u in cursor.fetchall():
            resultados.append({
                'tipo': 'Usuario', 'icono': 'fa-user', 'color': '#10b981',
                'titulo': u['nombre'] or 'Sin nombre', 'sub': u['email'],
                'url': url_for('admin.admin_usuarios') + f"?q={u['email']}"
            })
            
        # Buscar tiendas (max 3)
        cursor.execute("""
            SELECT usuario_id, nombre_tienda, numero_id 
            FROM perfil_vendedor 
            WHERE nombre_tienda LIKE %s OR numero_id LIKE %s 
            LIMIT 3
        """, (f"%{q}%", f"%{q}%"))
        for tv in cursor.fetchall():
            resultados.append({
                'tipo': 'Tienda', 'icono': 'fa-store', 'color': '#a855f7',
                'titulo': tv['nombre_tienda'], 'sub': f"ID: {tv['numero_id']}",
                'url': url_for('admin.solicitudes_vendedores') + f"?q={tv['nombre_tienda']}"
            })
            
        # Buscar vehículos (max 4)
        cursor.execute("""
            SELECT v.id, m.nombre as marca, mo.nombre as modelo, v.anio, v.precio 
            FROM vehiculos v 
            LEFT JOIN marcas m ON v.id_marca = m.id 
            LEFT JOIN modelos mo ON v.id_modelo = mo.id 
            WHERE m.nombre LIKE %s OR mo.nombre LIKE %s
            LIMIT 4
        """, (f"%{q}%", f"%{q}%"))
        for v in cursor.fetchall():
            resultados.append({
                'tipo': 'Vehículo', 'icono': 'fa-car', 'color': '#ff7043',
                'titulo': f"{v['marca']} {v['modelo']} {v['anio']}", 'sub': f"${v['precio']:,}",
                'url': url_for('admin.admin_vehiculos') + f"?q={v['id']}"
            })
            
        cursor.close()
    except Exception as e:
        print(f"Error búsqueda global: {e}")
        
    return {'resultados': resultados}

# ---------------------------------------------------------------
#  ADMINISTRAR USUARIOS
# ---------------------------------------------------------------
@admin_bp.route('/usuarios')
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def admin_usuarios():
    query = request.args.get('q', '').strip()
    rol_filter = request.args.get('rol', '')
    estado_filter = request.args.get('estado', '')
    
    base_query = "SELECT id, nombre, email, username, rol, estado FROM usuarios"
    where_clauses = []
    params = []
    
    if query:
        where_clauses.append("(nombre LIKE %s OR email LIKE %s OR username LIKE %s)")
        search_param = f"%{query}%"
        params.extend([search_param, search_param, search_param])

    if rol_filter:
        where_clauses.append("rol = %s")
        params.append(rol_filter)

    if estado_filter:
        where_clauses.append("estado = %s")
        params.append(estado_filter)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        
    base_query += " ORDER BY id DESC"

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(base_query, params)
    usuarios = [dict(u) for u in cursor.fetchall()]
    cursor.close()
    
    return render_template('admin/admin_usuarios.html', usuarios=usuarios)

@admin_bp.route("/usuario/<int:id>/vehiculos")
@admin_requerido
@requiere_roles('moderador')
def admin_vehiculos_usuario(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Verificación de Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u_db = cursor.fetchone()
    if u_db and u_db['rol'] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("Operación restringida. No se permite la visualización de registros pertenecientes a la administración principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
    cursor.execute("""
        SELECT v.id, v.anio, v.precio, v.version, v.estado, v.id_usuario,
               COALESCE(
                   (SELECT url_imagen FROM imagenes_vehiculos iv WHERE iv.id_vehiculo = v.id ORDER BY iv.id ASC LIMIT 1),
                   v.imagen
               ) AS imagen,
               m.nombre AS marca, mo.nombre AS modelo
        FROM vehiculos v
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        WHERE v.id_usuario = %s
        ORDER BY v.id DESC
    """, (id,))
    vehiculos = cursor.fetchall()

    cursor.execute("SELECT id, nombre, email FROM usuarios WHERE id=%s", (id,))
    usuario_row = cursor.fetchone()
    cursor.close()

    if not usuario_row:
        flash("El registro de usuario solicitado no fue encontrado.", "error")
        return redirect(url_for('admin.dashboard'))
    
    usuario = dict(usuario_row)
    return render_template("admin/admin_vehiculos_usuario.html", vehiculos=vehiculos, usuario=usuario)

@admin_bp.route('/usuarios/crear', methods=['GET', 'POST'])
@admin_requerido
@requiere_roles('moderador')
def crear_usuario():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        rol = request.form.get('rol')

        password_hash = generate_password_hash(password)

        try:
            cursor.execute("""
                INSERT INTO usuarios (nombre, apellidos, telefono, username, email, password, rol, estado, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo', NOW())
            """, (nombre, apellidos, telefono, username, email, password_hash, rol))
            conexion.commit()
            flash("El usuario ha sido registrado exitosamente en el sistema.", "success")
            return redirect(url_for('admin.admin_usuarios'))
        except Exception as e:
            print("ERROR CREANDO USUARIO:", e)
            flash("Error en el registro del usuario. Por favor, verifique que los datos no estén duplicados.", "danger")
        finally:
            cursor.close()
            
    return render_template('admin/admin_crear_usuario.html')

@admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_activo_requerido 
@admin_requerido
@requiere_roles('moderador', 'editor') # Permitimos editor porque usuarios puede significar vendedores
def editar_usuario(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 0. Verificamos quién es el usuario antes de empezar
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    usuario_db = cursor.fetchone()
    if not usuario_db:
        cursor.close()
        flash("El registro de usuario que intenta editar no se encuentra disponible.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
        
    rol_actual = usuario_db['rol']
    soy_superadmin = (session.get('rol') == 'superadmin')
    
    # NUEVA REGLA: NADIE (excepto otro Superadmin) puede entrar a editar a un Superadmin
    if rol_actual == 'superadmin' and not soy_superadmin:
        cursor.close()
        flash("Acceso denegado. No posee privilegios para modificar cuentas de nivel Administrador Principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        username = request.form['username']
        
        # El rol puede venir vacío si el input está deshabilitado en el frontend
        nuevo_rol = request.form.get('rol', rol_actual)
        
        roles_admin = ['superadmin', 'admin', 'moderador', 'editor']
        
        # 2. Restricción: Si se intenta subir a admin o cambiar rol admin, solo Superadmin puede
        if nuevo_rol != rol_actual:
            if (rol_actual in roles_admin or nuevo_rol in roles_admin) and not soy_superadmin:
                flash("Acceso restringido. La gestión de roles administrativos es de carácter exclusivo del Administrador Principal.", "danger")
                return redirect(url_for('admin.admin_usuarios'))

        # 3. Proceder con el registro
        cursor.execute("UPDATE usuarios SET nombre=%s, email=%s, username=%s, rol=%s WHERE id=%s", (nombre, email, username, nuevo_rol, id))
        conexion.commit()
        cursor.close()
        registrar_log('editar_usuario', 'usuario', id, f'Usuario #{id} editado: nombre={nombre}, rol={nuevo_rol}')
        flash("La información del usuario ha sido actualizada exitosamente.", "success")
        return redirect(url_for('admin.admin_usuarios'))

    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (id,))
    usuario_row = cursor.fetchone()
    cursor.close()
    usuario = dict(usuario_row) if usuario_row else {}
    return render_template('admin/usuario_editar.html', usuario=usuario)

@admin_bp.route('/usuarios/bloquear/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def bloquear_usuario(id):
    if 'usuario_id' in session and id == session.get('usuario_id'):
        flash("Operación no permitida. No puede aplicar restricciones de bloqueo a su propia cuenta.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
    
    cursor = conexion.cursor()
    
    # Verificación de Superadmin: No se puede bloquear a un Superadmin si no eres Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u = cursor.fetchone()
    if u and u[0] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("Acceso denegado. No posee la autoridad necesaria para bloquear la cuenta del Administrador Principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
        
    cursor.execute("UPDATE usuarios SET estado='bloqueado' WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    registrar_log('ban_usuario', 'usuario', id, f'Usuario #{id} bloqueado')
    flash("El acceso del usuario ha sido suspendido exitosamente.", "warning")
    return redirect(url_for('admin.admin_usuarios'))

@admin_bp.route('/usuarios/desbloquear/<int:id>', methods=['POST'])
@login_activo_requerido 
@admin_requerido
@requiere_roles('moderador')
def desbloquear_usuario(id):
    cursor = conexion.cursor()
    
    # Verificación de Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u = cursor.fetchone()
    if u and u[0] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("Operación restringida. Gestión autorizada únicamente para el Administrador Principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    cursor.execute("UPDATE usuarios SET estado='activo' WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    registrar_log('desbloquear_usuario', 'usuario', id, f'Usuario #{id} desbloqueado')
    flash("Se ha activado el acceso del usuario correctamente.", "success")
    return redirect(url_for('admin.admin_usuarios'))

@admin_bp.route('/usuarios/borrar/<int:id>', methods=['POST'])
@login_activo_requerido 
@admin_requerido
@requiere_roles('moderador')
def borrar_usuario(id):
    cursor = conexion.cursor()
    
    # Verificación de Superadmin: No se puede eliminar a un Superadmin si no eres Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u = cursor.fetchone()
    if u and u[0] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("No dispone de los permisos necesarios para eliminar la cuenta del administrador principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    conexion.commit()
    cursor.close()
    registrar_log('borrar_usuario', 'usuario', id, f'Usuario #{id} eliminado permanentemente')
    flash("La cuenta de usuario ha sido eliminada del sistema.", "success")
    return redirect(url_for('admin.admin_usuarios'))

@admin_bp.route('/usuarios/ver/<int:id>')
@login_activo_requerido 
@admin_requerido
@requiere_roles('moderador')
def ver_usuario(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Verificación de Superadmin
    cursor.execute("SELECT id, nombre, email, username, foto, rol, estado, fecha_registro, ultima_sesion, telefono FROM usuarios WHERE id = %s", (id,))
    u_db = cursor.fetchone()
    if not u_db:
        cursor.close()
        flash("Usuario no encontrado", "error")
        return redirect(url_for('admin.admin_usuarios'))
        
    soy_superadmin = (session.get('rol') == 'superadmin')
    if u_db['rol'] == 'superadmin' and not soy_superadmin:
        cursor.close()
        flash("No tiene autorización para visualizar los detalles de la gestión administrativa principal.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
        
    usuario = dict(u_db)
        
    cursor.execute("SELECT COUNT(*) as p_count FROM vehiculos WHERE id_usuario = %s", (id,))
    pub_data = cursor.fetchone()
    pub_count = pub_data['p_count'] if pub_data else 0
    
    cursor.execute("SELECT COUNT(*) as f_count FROM favoritos WHERE id_usuario = %s", (id,))
    fav_data = cursor.fetchone()
    fav_count = fav_data['f_count'] if fav_data else 0
    
    cursor.close()
    
    return render_template('admin/usuario_ver.html', usuario=usuario, pub_count=pub_count, fav_count=fav_count)

@admin_bp.route('/usuarios/rol/<int:id>', methods=['POST'])
@login_activo_requerido 
@admin_requerido
@requiere_roles('moderador')
def cambiar_rol(id):
    nuevo_rol = request.form.get('rol')
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 1. Obtener rol actual
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    usuario_db = cursor.fetchone()
    if not usuario_db:
        cursor.close()
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('admin.admin_usuarios'))
        
    rol_actual = usuario_db['rol']
    roles_admin = ['superadmin', 'admin', 'moderador', 'editor']
    soy_superadmin = (session.get('rol') == 'superadmin')
    
    # 2. Protección: Solo superadmin cambia roles administrativos
    if (rol_actual in roles_admin or nuevo_rol in roles_admin) and not soy_superadmin:
        cursor.close()
        flash("No tiene autorización para gestionar roles de nivel administrativo.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    # 3. Guardar cambios
    cursor.execute("UPDATE usuarios SET rol = %s WHERE id = %s", (nuevo_rol, id))
    conexion.commit()
    cursor.close()
    
    registrar_log('cambiar_rol_rapido', 'usuario', id, f'Rol cambiado de {rol_actual} a {nuevo_rol}')
    flash(f"El rol del usuario ha sido actualizado a {nuevo_rol.capitalize()}.", "success")
    return redirect(url_for('admin.admin_usuarios'))

@admin_bp.route('/usuarios/activar/<int:id>', methods=['POST'])
@login_activo_requerido 
@admin_requerido
def activar_usuario(id):
    cursor = conexion.cursor()
    # Verificación Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u = cursor.fetchone()
    if u and u[0] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("Solo el administrador principal puede realizar gestiones sobre esta cuenta.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    cursor.execute("UPDATE usuarios SET estado='activo' WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    flash("Acceso de usuario restaurado correctamente.", "success")
    return redirect(url_for('admin.admin_usuarios'))

@admin_bp.route('/usuarios/desactivar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
def desactivar_usuario(id):
    cursor = conexion.cursor()
    # Verificación Superadmin
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (id,))
    u = cursor.fetchone()
    if u and u[0] == 'superadmin' and session.get('rol') != 'superadmin':
        cursor.close()
        flash("Solo la administración principal tiene facultades para gestionar esta cuenta.", "danger")
        return redirect(url_for('admin.admin_usuarios'))

    cursor.execute("UPDATE usuarios SET estado='inactivo' WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    flash("La cuenta de usuario ha sido desactivada temporalmente.", "warning")
    return redirect(url_for('admin.admin_usuarios'))

# ====================================================
# GESTIÓN DE SOLICITUDES DE VENDEDORES
# ====================================================
@admin_bp.route('/solicitudes-vendedores')
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def solicitudes_vendedores():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        sql = """
            SELECT pv.*, u.nombre AS nombre_usuario, u.email AS email_usuario
            FROM perfil_vendedor pv
            LEFT JOIN usuarios u ON pv.usuario_id = u.id
            WHERE pv.estado_verificacion = 'pendiente' 
            ORDER BY pv.id DESC
        """
        cursor.execute(sql)
        solicitudes = cursor.fetchall()
        
        print(f"DEBUG: Se encontraron {len(solicitudes)} solicitudes pendientes.")

    except Exception as e:
        print(f"Error SQL: {e}")
        solicitudes = []
    finally:
        cursor.close()
    
    return render_template('admin/solicitudes.html', solicitudes=solicitudes)

@admin_bp.route('/vendedores/aprobar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def aprobar_vendedor(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT nombre_tienda, email_comercial FROM perfil_vendedor WHERE id = %s", (id,))
        vendedor = cursor.fetchone()

        cursor.execute("UPDATE perfil_vendedor SET estado_verificacion = 'aprobado' WHERE id = %s", (id,))
        
        # Registrar auditoría
        cursor.execute("""
            INSERT INTO logs_admin (id_admin, nombre_admin, accion, entidad, id_entidad, descripcion, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session.get('usuario_id'), 
            session.get('nombre_usuario', 'Admin'), 
            'Aprobación Tienda', 
            'PerfilVendedor', 
            id, 
            f"Aprobó la tienda {vendedor.get('nombre_tienda', 'Desconocido')} de manera manual", 
            request.remote_addr
        ))
        
        conexion.commit()

        if vendedor and vendedor.get('email_comercial'):
            try:
                asunto = "Notificación: Activación de Tienda Comercial"
                mensaje = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #10b981;">Su solicitud ha sido aprobada</h2>
                    <p>Estimado/a titular de <strong>{vendedor['nombre_tienda']}</strong>,</p>
                    <p>Le informamos que ya dispone de acceso total a su <strong>Panel de Vendedor</strong>.</p>
                    <a href="{url_for('vendedor.dashboard', _external=True)}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Acceder al Panel</a>
                </div>
                """
                enviar_notificacion_email(vendedor['email_comercial'], asunto, mensaje)
            except Exception as e_mail:
                print(f"[ERROR] El usuario fue aprobado pero falló el correo: {e_mail}")

        flash("La solicitud del vendedor ha sido aprobada correctamente.", "success")

    except Exception as e:
        if conexion: conexion.rollback()
        flash(f"Error al aprobar: {e}", "danger")
        print(f"Error crítico: {e}")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.solicitudes_vendedores'))

@admin_bp.route('/vendedores/rechazar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def rechazar_vendedor(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT nombre_tienda, email_comercial FROM perfil_vendedor WHERE id = %s", (id,))
        vendedor = cursor.fetchone()

        cursor.execute("UPDATE perfil_vendedor SET estado_verificacion = 'rechazado' WHERE id = %s", (id,))
        
        # Registrar auditoría
        cursor.execute("""
            INSERT INTO logs_admin (id_admin, nombre_admin, accion, entidad, id_entidad, descripcion, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session.get('usuario_id'), 
            session.get('nombre_usuario', 'Admin'), 
            'Rechazo Tienda', 
            'PerfilVendedor', 
            id, 
            f"Rechazó la tienda {vendedor.get('nombre_tienda', 'Desconocido')} de manera manual", 
            request.remote_addr
        ))
        
        conexion.commit()

        if vendedor and vendedor.get('email_comercial'):
            try:
                asunto = "Actualización: Estado de su solicitud comercial"
                mensaje = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #ef4444;">Solicitud No Aprobada</h2>
                    <p>Estimado/a titular de <strong>{vendedor['nombre_tienda']}</strong>,</p>
                    <p>Le comunicamos que en este momento no ha sido posible aprobar su cuenta. Por favor, revise la documentación adjunta en su perfil.</p>
                    <a href="{url_for('vendedor.promo', _external=True)}" style="background-color: #ef4444; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Revisar Perfil</a>
                </div>
                """
                enviar_notificacion_email(vendedor['email_comercial'], asunto, mensaje)
            except Exception as e_mail:
                print(f"[ERROR] Usuario rechazado pero falló el correo: {e_mail}")

        flash("La solicitud de registro de tienda ha sido rechazada.", "warning")

    except Exception as e:
        if conexion: conexion.rollback()
        flash(f"Error al rechazar: {e}", "danger")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.solicitudes_vendedores'))

# ---------------------------------------------------------------
#  ADMINISTRAR VEHÍCULOS
# ---------------------------------------------------------------
@admin_bp.route('/vehiculos', methods=['GET'])
@admin_requerido
@requiere_roles('editor')
def admin_vehiculos():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    marca = request.args.get('marca')
    propietario = request.args.get('propietario')
    precio_min = request.args.get('precio_min')
    precio_max = request.args.get('precio_max')
    estado = request.args.get('estado')

    query = """
    SELECT v.id, v.id_usuario, v.id_marca, v.id_modelo, v.anio, 
           v.kilometraje, v.precio, v.estado,
           COALESCE(
               (SELECT url_imagen FROM imagenes_vehiculos iv WHERE iv.id_vehiculo = v.id ORDER BY iv.id ASC LIMIT 1),
               v.imagen
           ) AS imagen,
           u.nombre AS propietario, m.nombre AS marca, mo.nombre AS modelo
    FROM vehiculos v
    LEFT JOIN usuarios u ON v.id_usuario = u.id
    LEFT JOIN marcas m ON v.id_marca = m.id
    LEFT JOIN modelos mo ON v.id_modelo = mo.id
    WHERE 1=1
    """
    params = []

    if marca:
        query += " AND m.nombre LIKE %s"
        params.append(f"%{marca}%")
    if propietario:
        query += " AND u.nombre LIKE %s"
        params.append(f"%{propietario}%")
    if precio_min:
        query += " AND v.precio >= %s"
        params.append(precio_min)
    if precio_max:
        query += " AND v.precio <= %s"
        params.append(precio_max)
    if estado:
        query += " AND v.estado = %s"
        params.append(estado)

    query += " ORDER BY v.id DESC"

    cursor.execute(query, params)
    vehiculos = cursor.fetchall()
    cursor.close()

    return render_template('admin/admin_vehiculos.html', vehiculos=vehiculos)

# ---------------------------------------------------------------
#  CREAR VEHÍCULO
# ---------------------------------------------------------------
@admin_bp.route('/vehiculos/crear', methods=['GET', 'POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def crear_vehiculo():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        try:
            id_marca = request.form.get('id_marca')
            id_modelo = request.form.get('id_modelo')
            anio = request.form.get('anio')
            precio = request.form.get('precio')
            kilometraje = request.form.get('kilometraje')
            version = request.form.get('version')
            ciudad = request.form.get('ciudad')
            placa = request.form.get('placa', 'PENDIENTE').upper()
            id_usuario = session.get('usuario_id')

            archivos = request.files.getlist('imagen[]')
            
            ruta_imagen_principal = None

            if archivos and archivos[0].filename:
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'vehiculos')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                archivo_principal = archivos[0]
                
                filename = secure_filename(archivo_principal.filename)
                nombre_unico = f"{int(datetime.now().timestamp() * 1000)}_{filename}"
                
                ruta_fisica = os.path.join(upload_folder, nombre_unico)
                archivo_principal.save(ruta_fisica)
                    
                # SUBIR A CLOUDINARY
                from helpers.cloudinary_utils import upload_file_to_cloudinary
                secure_url = upload_file_to_cloudinary(ruta_fisica, folder="drivemarket/vehiculos")
                
                if secure_url:
                    ruta_imagen_principal = secure_url
                else:
                    ruta_imagen_principal = f"uploads/vehiculos/{nombre_unico}"
                
                # Limpiar temporal si se subió a Cloudinary
                if secure_url:
                    try: os.remove(ruta_fisica)
                    except: pass

            sql = """
                INSERT INTO vehiculos 
                (
                    id_usuario, id_marca, id_modelo, anio, precio, kilometraje, 
                    version, ciudad_venta, estado, 
                    imagen, fecha_publicacion,
                    placa, ciudad_placa, id_tipo, id_color, negociable, dueno
                )
                VALUES 
                (
                    %s, %s, %s, %s, %s, %s, 
                    %s, %s, 'activo', 
                    %s, NOW(),
                    %s, %s, 1, 1, 'No', 'Administrador'
                )
            """
            
            val = (id_usuario, id_marca, id_modelo, anio, precio, kilometraje, 
                   version, ciudad, ruta_imagen_principal, placa, ciudad)
            
            cursor.execute(sql, val)
            conexion.commit()

            flash(f"Publicación de vehículo creada exitosamente con {len(archivos)} imágenes procesadas.", "success")
            return redirect(url_for('admin.admin_vehiculos'))

        except Exception as e:
            if conexion: conexion.rollback()
            print("Error al crear vehículo:", e)
            flash(f"Error técnico al guardar: {e}", "danger")

    cursor.execute("SELECT * FROM marcas ORDER BY nombre ASC")
    marcas = cursor.fetchall()
    cursor.execute("SELECT * FROM modelos ORDER BY nombre ASC")
    modelos = cursor.fetchall()
    cursor.close()

    return render_template('admin/vehiculo_crear.html', marcas=marcas, modelos=modelos)

# ---------------------------------------------------------------
#  ACCIONES VEHÍCULOS
# ---------------------------------------------------------------
@admin_bp.route('/vehiculos/bloquear/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor', 'moderador') # moderador tb puede bloquear vehiculos reportados
def bloquear_vehiculo(id):
    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE vehiculos SET estado = 'bloqueado' WHERE id = %s", (id,))
        conexion.commit()
        flash('El vehículo ha sido bloqueado conforme a las políticas de cumplimiento administrativo.', 'warning')
    except Exception as e:
        if conexion: conexion.rollback()
        print(f"Error bloqueando vehículo: {e}")
        flash('Error al bloquear vehículo', 'danger')
    finally:
        if cursor: cursor.close()
    
    return redirect(request.referrer or url_for('admin.admin_vehiculos'))

@admin_bp.route("/vehiculos/activar/<int:id>", methods=["POST"])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor', 'moderador')
def activar_vehiculo(id):
    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE vehiculos SET estado = 'activo' WHERE id = %s", (id,))
        conexion.commit()
        flash("La publicación del vehículo ha sido activada.", "success")
    except Exception as e:
        if conexion: conexion.rollback()
        print(f"Error activando vehículo: {e}")
        flash('Error al activar vehículo', 'danger')
    finally:
        if cursor: cursor.close()

    return redirect(request.referrer or url_for("admin.admin_vehiculos"))

@admin_bp.route("/vehiculos/desactivar/<int:id>", methods=["POST"])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor', 'moderador')
def desactivar_vehiculo(id):
    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE vehiculos SET estado='inactivo' WHERE id=%s", (id,))
        conexion.commit()
        flash("La publicación ha sido pausada correctamente.", "info")
    except Exception as e:
        if conexion: conexion.rollback()
        print(f"Error desactivando: {e}")
        flash("Error al desactivar vehículo", "danger")
    finally:
        if cursor: cursor.close()

    return redirect(request.referrer or url_for("admin.admin_vehiculos"))

@admin_bp.route('/vehiculos/borrar/<int:id>', methods=['POST'])
@login_activo_requerido 
@admin_requerido
@requiere_roles('editor')
def borrar_vehiculo(id):
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM vehiculos WHERE id = %s", (id,))
    conexion.commit()
    cursor.close()
    flash("El vehículo ha sido eliminado del sistema de inventario permanentemente.", "success")
    return redirect(url_for('admin.admin_vehiculos'))

@admin_bp.route('/vehiculos/editar/<int:id>', methods=['GET', 'POST'])
@login_activo_requerido
def editar_vehiculo(id):
    """
    Permite editar un vehículo.
    - Admins/Editor: pueden editar CUALQUIER vehículo
    - Usuarios normales: solo pueden editar SUS PROPIOS vehículos
    """
    print(f"\n🔵🔵🔵 EDITANDO VEHÍCULO ID: {id} 🔵🔵🔵")
    print(f"👤 Usuario ID: {session.get('usuario_id')}, Rol: {session.get('rol')}")
    
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Obtener datos del vehículo (sin filtro de usuario aún)
    cursor.execute("""
        SELECT v.*, m.nombre AS marca_nombre, mo.nombre AS modelo_nombre,
               u.nombre AS propietario_nombre, u.email AS propietario_email
        FROM vehiculos v
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        LEFT JOIN usuarios u ON v.id_usuario = u.id
        WHERE v.id = %s
    """, (id,))
    vehiculo = cursor.fetchone()

    if not vehiculo:
        flash("Vehículo no encontrado.", "danger")
        cursor.close()
        return redirect(url_for('admin.admin_vehiculos'))

    # 🔐 VERIFICACIÓN DE PERMISOS
    es_admin = session.get('rol') in ['admin', 'superadmin', 'editor', 'moderador']
    es_propietario = session.get('usuario_id') == vehiculo['id_usuario']
    
    print(f"🔐 ¿Es admin? {es_admin}")
    print(f"🔐 ¿Es propietario? {es_propietario}")
    
    if not (es_admin or es_propietario):
        flash("No tienes permiso para editar este vehículo.", "danger")
        cursor.close()
        return redirect(url_for('admin.admin_vehiculos') if es_admin else url_for('users.mis_vehiculos'))

    if not es_admin and vehiculo.get('estado') == 'bloqueado':
        flash("🚫 Este vehículo ha sido bloqueado por un administrador. Si tienes alguna duda, comunícate con soporte.", "error")
        cursor.close()
        return redirect(url_for('users.mis_vehiculos'))

    # 📸 Obtener imágenes de la galería secundaria
    cursor.execute("SELECT * FROM imagenes_vehiculos WHERE id_vehiculo = %s ORDER BY id ASC", (id,))
    imagenes = cursor.fetchall()

    # Obtener marcas y modelos para el formulario
    cursor.execute("SELECT id, nombre FROM marcas ORDER BY nombre")
    marcas = cursor.fetchall()
    
    cursor.execute("SELECT id, nombre, id_marca FROM modelos ORDER BY nombre")
    modelos = cursor.fetchall()

    if request.method == 'POST':
        print("📝 PROCESANDO FORMULARIO POST")
        
        # Capturar datos del formulario
        id_marca = request.form.get('id_marca')
        id_modelo = request.form.get('id_modelo')
        anio = request.form.get('anio')
        precio = request.form.get('precio')
        kilometraje = request.form.get('kilometraje')
        version = request.form.get('version')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')
        transmision = request.form.get('transmision') or None
        combustible = request.form.get('combustible') or None
        motor = request.form.get('motor') or None
        traccion = request.form.get('traccion') or None
        puertas = request.form.get('puertas') or None
        ciudad_venta = request.form.get('ciudad') or None
        placa = request.form.get('placa') or None
        
        print("📋 DATOS RECIBIDOS:")
        print(f"  - id_marca: {id_marca}")
        print(f"  - id_modelo: {id_modelo}")
        print(f"  - anio: {anio}")
        print(f"  - precio: {precio}")
        print(f"  - kilometraje: {kilometraje}")
        print(f"  - version: {version}")
        print(f"  - estado: {estado}")
        
        # Manejo de imagen
        imagen_archivo = request.files.get('imagen')
        nueva_imagen = vehiculo['imagen']  # Mantener imagen actual por defecto
        
        if imagen_archivo and imagen_archivo.filename:
            print(f"🖼️ Se recibió nueva imagen: {imagen_archivo.filename}")
            try:
                from admin_routes import guardar_imagen_vehiculo, eliminar_imagen_vehiculo
                
                nombre_archivo = guardar_imagen_vehiculo(imagen_archivo)
                if nombre_archivo:
                    nueva_imagen = nombre_archivo
                    # Eliminar imagen anterior si no es default
                    if vehiculo['imagen'] and vehiculo['imagen'] != 'default.jpg':
                        eliminar_imagen_vehiculo(vehiculo['imagen'])
                    print(f"✅ Imagen guardada: {nombre_archivo}")
                else:
                    print("❌ No se pudo guardar la imagen")
                    flash("No se pudo guardar la imagen", "warning")
            except Exception as e:
                print(f"❌ Error al guardar imagen: {e}")
                flash(f"Error al procesar imagen: {str(e)}", "danger")
        
        # Preparar valores para UPDATE
        valores = {
            'id_marca': id_marca,
            'id_modelo': id_modelo,
            'anio': anio,
            'precio': precio,
            'kilometraje': kilometraje,
            'version': version,
            'descripcion': descripcion,
            'estado': estado,
            'imagen': nueva_imagen,
            'transmision': transmision,
            'combustible': combustible,
            'motor': motor,
            'traccion': traccion,
            'puertas': puertas,
            'ciudad_venta': ciudad_venta,
            'placa': placa,
            'id': id
        }
        
        # Verificar que ningún valor sea None
        for key, value in valores.items():
            if value is None:
                print(f"⚠️ {key} es None, reemplazando con string vacío")
                valores[key] = ''
        
        try:
            # Ejecutar UPDATE - Los admins pueden editar cualquier vehículo
            # Los propietarios solo pueden editar si el WHERE incluye id_usuario
            if es_admin:
                sql = """
                    UPDATE vehiculos SET 
                        id_marca = %s, 
                        id_modelo = %s, 
                        anio = %s, 
                        precio = %s, 
                        kilometraje = %s, 
                        version = %s, 
                        descripcion = %s,
                        estado = %s, 
                        imagen = %s,
                        transmision = %s,
                        combustible = %s,
                        motor = %s,
                        traccion = %s,
                        puertas = %s,
                        ciudad_venta = %s,
                        placa = %s
                    WHERE id = %s
                """
                params = (
                    valores['id_marca'],
                    valores['id_modelo'],
                    valores['anio'],
                    valores['precio'],
                    valores['kilometraje'],
                    valores['version'],
                    valores['descripcion'],
                    valores['estado'],
                    valores['imagen'],
                    valores['transmision'],
                    valores['combustible'],
                    valores['motor'],
                    valores['traccion'],
                    valores['puertas'],
                    valores['ciudad_venta'],
                    valores['placa'],
                    valores['id']
                )
            else:
                # Propietario: solo puede editar si el vehículo le pertenece
                sql = """
                    UPDATE vehiculos SET 
                        id_marca = %s, 
                        id_modelo = %s, 
                        anio = %s, 
                        precio = %s, 
                        kilometraje = %s, 
                        version = %s, 
                        descripcion = %s,
                        estado = %s, 
                        imagen = %s,
                        transmision = %s,
                        combustible = %s,
                        motor = %s,
                        traccion = %s,
                        puertas = %s,
                        ciudad_venta = %s,
                        placa = %s
                    WHERE id = %s AND id_usuario = %s
                """
                params = (
                    valores['id_marca'],
                    valores['id_modelo'],
                    valores['anio'],
                    valores['precio'],
                    valores['kilometraje'],
                    valores['version'],
                    valores['descripcion'],
                    valores['estado'],
                    valores['imagen'],
                    valores['transmision'],
                    valores['combustible'],
                    valores['motor'],
                    valores['traccion'],
                    valores['puertas'],
                    valores['ciudad_venta'],
                    valores['placa'],
                    valores['id'],
                    session['usuario_id']
                )
            
            print(f"📝 SQL: {sql}")
            print(f"📝 VALORES: {params}")
            
            cursor.execute(sql, params)
            conexion.commit()
            
            print(f"✅ {cursor.rowcount} fila(s) actualizada(s)")
            if cursor.rowcount > 0:
                flash("✅ Vehículo actualizado correctamente", "success")
                # Redirigir según el rol
                if es_admin:
                    return redirect(url_for('admin.admin_vehiculos'))
                else:
                    return redirect(url_for('users.mis_vehiculos'))
            else:
                flash("No se realizaron cambios en el vehículo", "warning")
                
        except Exception as e:
            conexion.rollback()
            print(f"❌ Error DB: {e}")
            import traceback
            traceback.print_exc()
            flash(f"Error al actualizar: {str(e)}", "danger")
    
    cursor.close()
    
    # Determinar a qué template redirigir según el rol
    template_name = 'admin/vehiculo_editar.html' if es_admin else 'users/editar_vehiculo.html'
    
    return render_template(template_name, 
                          vehiculo=vehiculo, 
                          marcas=marcas, 
                          modelos=modelos,
                          imagenes=imagenes,
                          es_admin=es_admin)

# ---------------------------------------------------------------
#  GESTIÓN DE GALERÍA DE IMÁGENES (ADMIN / USUARIO)
# ---------------------------------------------------------------
@admin_bp.route('/vehiculo/<int:id>/galeria/subir', methods=['POST'])
@login_activo_requerido
def subir_foto_galeria(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Verificar propiedad
    cursor.execute("SELECT id_usuario FROM vehiculos WHERE id = %s", (id,))
    v = cursor.fetchone()
    if not v:
        cursor.close()
        return "Vehículo no encontrado", 404
        
    es_admin = session.get('rol') in ['admin', 'superadmin', 'editor', 'moderador']
    if not (es_admin or session.get('usuario_id') == v['id_usuario']):
        cursor.close()
        return "Sin permisos", 403

    archivos = request.files.getlist('fotos[]')
    if not archivos:
        cursor.close()
        flash("No se seleccionaron archivos.", "warning")
        return redirect(request.referrer)

    from werkzeug.utils import secure_filename
    import os, uuid
    
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'vehiculos')
    os.makedirs(upload_folder, exist_ok=True)
    
    subidos = 0
    for file in archivos:
        if file and file.filename:
            original_ext = os.path.splitext(file.filename)[1].lower()
            if original_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                nombre_unico = f"gal_{id}_{uuid.uuid4().hex}{original_ext}"
                ruta_fisica = os.path.join(upload_folder, nombre_unico)
                file.save(ruta_fisica)
                
                # Opcional: marca de agua... (como se hace en vendedores.py si se desea)
                
                rel_path = f"uploads/vehiculos/{nombre_unico}"
                cursor.execute("INSERT INTO imagenes_vehiculos (id_vehiculo, url_imagen) VALUES (%s, %s)", (id, rel_path))
                subidos += 1
    
    conexion.commit()
    cursor.close()
    
    if subidos > 0:
        flash(f"Se han añadido {subidos} fotos a la galería. ✨", "success")
    else:
        flash("No se pudo subir ninguna foto. Verifica el formato.", "danger")
        
    return redirect(request.referrer)

@admin_bp.route('/vehiculo/<int:id>/galeria/eliminar/<int:img_id>', methods=['POST'])
@login_activo_requerido
def eliminar_foto_galeria(id, img_id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Verificar propiedad
    cursor.execute("SELECT id_usuario FROM vehiculos WHERE id = %s", (id,))
    v = cursor.fetchone()
    if not v:
        cursor.close()
        return "Vehículo no encontrado", 404
        
    es_admin = session.get('rol') in ['admin', 'superadmin', 'editor', 'moderador']
    if not (es_admin or session.get('usuario_id') == v['id_usuario']):
        cursor.close()
        return "Sin permisos", 403

    # Obtener ruta para borrar de disco
    cursor.execute("SELECT url_imagen FROM imagenes_vehiculos WHERE id = %s AND id_vehiculo = %s", (img_id, id))
    img = cursor.fetchone()
    if img:
        ruta_fisica = os.path.join(current_app.root_path, 'static', img['url_imagen'].replace('/', os.sep))
        if os.path.exists(ruta_fisica):
            try: os.remove(ruta_fisica)
            except: pass
            
        cursor.execute("DELETE FROM imagenes_vehiculos WHERE id = %s", (img_id,))
        conexion.commit()
        flash("Foto eliminada de la galería.", "info")
    
    cursor.close()
    return redirect(request.referrer)
# ---------------------------------------------------------------
#  ADMINISTRAR REPORTES
# ---------------------------------------------------------------
@admin_bp.route("/reportes")
@admin_requerido
@requiere_roles('moderador')
def admin_reportes():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
    SELECT r.id, r.titulo, r.detalle, r.estado, r.fecha, 
           u.nombre AS usuario, m.nombre AS marca, mo.nombre AS modelo,
           v.anio, v.kilometraje, v.precio, v.imagen
    FROM reportes r
    LEFT JOIN usuarios u ON r.id_usuario = u.id
    LEFT JOIN vehiculos v ON r.id_vehiculo = v.id
    LEFT JOIN marcas m ON v.id_marca = m.id
    LEFT JOIN modelos mo ON v.id_modelo = mo.id
    ORDER BY r.id DESC
    """)
    reportes = cursor.fetchall()
    cursor.close()
    return render_template('admin/admin_reportes.html', reportes=reportes)

@admin_bp.route("/vehiculos/<int:id>/reportes")
@admin_requerido
@requiere_roles('moderador')
def reportes_vehiculo(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT v.id, v.anio, v.precio, v.imagen, m.nombre AS marca, mo.nombre AS modelo 
        FROM vehiculos v
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        WHERE v.id = %s
    """, (id,))
    vehiculo = cursor.fetchone()

    cursor.execute("""
        SELECT r.id, r.titulo, r.detalle, r.estado, r.fecha, u.nombre AS usuario
        FROM reportes r
        LEFT JOIN usuarios u ON u.id = r.id_usuario
        WHERE r.id_vehiculo = %s
        ORDER BY r.id DESC
    """, (id,))
    reportes = cursor.fetchall()
    cursor.close()

    return render_template("admin/reportes_vehiculo.html", vehiculo=vehiculo, reportes=reportes)

@admin_bp.route("/reportes/revisado/<int:id>", methods=["POST"])
@admin_requerido
@requiere_roles('moderador')
def marcar_revisado(id):
    cursor = conexion.cursor()
    cursor.execute("UPDATE reportes SET estado='revisado' WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    flash("Reporte marcado como revisado ✔️", "success")
    return redirect(url_for("admin.admin_reportes"))

@admin_bp.route("/reportes/eliminar/<int:id>", methods=["POST"])
@admin_requerido
@requiere_roles('moderador')
def eliminar_reporte(id):
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM reportes WHERE id=%s", (id,))
    conexion.commit()
    cursor.close()
    flash("Reporte eliminado correctamente ❌", "success")
    return redirect(url_for("admin.admin_reportes"))

# ====================================================
# AJUSTES DE PERFIL
# ====================================================
@admin_bp.route('/ajustes', methods=['GET', 'POST'])
@login_activo_requerido
def ajustes():
    id_usuario = session.get('usuario_id')
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'actualizar_datos':
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            username = request.form.get('username')
            
            try:
                cursor.execute("UPDATE usuarios SET nombre=%s, email=%s, username=%s WHERE id=%s", 
                               (nombre, email, username, id_usuario))
                conexion.commit()
                session['nombre'] = nombre 
                session['username'] = username
                flash("Tus datos han sido actualizados. ✅", "success")
            except Exception as e:
                flash(f"Error al actualizar (posible usuario/email duplicado). ❌", "danger")

        elif accion == 'cambiar_password':
            pass_actual = request.form.get('pass_actual', '').strip()
            pass_nuevo = request.form.get('pass_nuevo', '')
            pass_confirmar = request.form.get('pass_confirmar', '')

            cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_usuario,))
            user_db = cursor.fetchone()

            if user_db and check_password_hash(user_db['password'], pass_actual):
                if pass_nuevo == pass_confirmar:
                    nuevo_hash = generate_password_hash(pass_nuevo)
                    cursor.execute("UPDATE usuarios SET password=%s WHERE id=%s", (nuevo_hash, id_usuario))
                    conexion.commit()
                    flash("Contraseña actualizada correctamente. 🔒", "success")
                else:
                    flash("Las contraseñas nuevas no coinciden. ⚠️", "warning")
            else:
                flash("La contraseña actual es incorrecta. ⛔", "danger")
        
        return redirect(url_for('admin.ajustes'))

    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (id_usuario,))
    mi_usuario_row = cursor.fetchone()
    cursor.close()
    mi_usuario = dict(mi_usuario_row) if mi_usuario_row else {}
    return render_template('admin/ajustes.html', usuario=mi_usuario)

# ====================================================
# GESTIÓN DE PROMOCIONES (CARRUSEL)
# ====================================================
@admin_bp.route('/promociones', methods=['GET'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def admin_promociones():
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM promociones ORDER BY orden ASC, fecha_creacion DESC")
    promociones = cursor.fetchall()
    cursor.close()
    return render_template('admin/admin_promociones.html', promociones=promociones)

@admin_bp.route('/promociones/crear', methods=['GET', 'POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def crear_promocion():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        etiqueta = request.form.get('etiqueta')
        color_etiqueta = request.form.get('color_etiqueta', 'var(--orange)')
        texto_boton = request.form.get('texto_boton', 'Ver más')
        enlace_boton = request.form.get('enlace_boton', '#')
        orden = request.form.get('orden', 0)
        
        archivo = request.files.get('imagen')
        ruta_imagen = ''
        
        if archivo and archivo.filename:
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'promos')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(archivo.filename)
            nombre_unico = f"promo_{int(datetime.now().timestamp())}_{filename}"
            archivo.save(os.path.join(upload_folder, nombre_unico))
            ruta_imagen = f"uploads/promos/{nombre_unico}"
            
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                INSERT INTO promociones 
                (titulo, descripcion, etiqueta, color_etiqueta, texto_boton, enlace_boton, imagen, orden)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (titulo, descripcion, etiqueta, color_etiqueta, texto_boton, enlace_boton, ruta_imagen, orden))
            conexion.commit()
            flash("Promoción creada correctamente 📢", "success")
            return redirect(url_for('admin.admin_promociones'))
        except Exception as e:
            conexion.rollback()
            flash(f"Error al crear: {e}", "danger")
        finally:
            cursor.close()
            
    return render_template('admin/promocion_crear.html', promo=None)

@admin_bp.route('/promociones/editar/<int:id>', methods=['GET', 'POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def editar_promocion(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        etiqueta = request.form.get('etiqueta')
        color_etiqueta = request.form.get('color_etiqueta')
        texto_boton = request.form.get('texto_boton')
        enlace_boton = request.form.get('enlace_boton')
        orden = request.form.get('orden')
        
        cursor.execute("SELECT imagen FROM promociones WHERE id = %s", (id,))
        promo_actual = cursor.fetchone()
        ruta_imagen = promo_actual['imagen']
        
        archivo = request.files.get('imagen')
        if archivo and archivo.filename:
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'promos')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(archivo.filename)
            nombre_unico = f"promo_{int(datetime.now().timestamp())}_{filename}"
            archivo.save(os.path.join(upload_folder, nombre_unico))
            ruta_imagen = f"uploads/promos/{nombre_unico}"
            
        try:
            cursor.execute("""
                UPDATE promociones 
                SET titulo=%s, descripcion=%s, etiqueta=%s, color_etiqueta=%s, 
                    texto_boton=%s, enlace_boton=%s, imagen=%s, orden=%s
                WHERE id = %s
            """, (titulo, descripcion, etiqueta, color_etiqueta, texto_boton, enlace_boton, ruta_imagen, orden, id))
            conexion.commit()
            flash("Promoción actualizada correctamente ✔️", "success")
            return redirect(url_for('admin.admin_promociones'))
        except Exception as e:
            conexion.rollback()
            flash(f"Error al actualizar: {e}", "danger")
            
    cursor.execute("SELECT * FROM promociones WHERE id = %s", (id,))
    promo = cursor.fetchone()
    cursor.close()
    
    if not promo:
        flash("Promoción no encontrada", "danger")
        return redirect(url_for('admin.admin_promociones'))
        
    return render_template('admin/promocion_crear.html', promo=promo)

@admin_bp.route('/promociones/toggle/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def toggle_promocion(id):
    cursor = conexion.cursor()
    try:
        cursor.execute("UPDATE promociones SET activa = NOT activa WHERE id = %s", (id,))
        conexion.commit()
        flash("Estado de promoción actualizado", "success")
    except Exception as e:
        conexion.rollback()
        flash("Error al actualizar estado", "danger")
    finally:
        cursor.close()
    return redirect(url_for('admin.admin_promociones'))

@admin_bp.route('/promociones/borrar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('editor')
def borrar_promocion(id):
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM promociones WHERE id = %s", (id,))
        conexion.commit()
        flash("Promoción eliminada correctamente 🗑️", "success")
    except Exception as e:
        conexion.rollback()
        flash("Error al eliminar", "danger")
    finally:
        cursor.close()
    return redirect(url_for('admin.admin_promociones'))


# ================================================================
#  SISTEMA DE REPORTES DE USUARIOS
# ================================================================

@admin_bp.route('/reportes-usuarios')
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def reportes_usuarios():
    tipo_filter = request.args.get('tipo', '')
    estado_filter = request.args.get('estado', '')
    motivo_filter = request.args.get('motivo', '')

    sql = """
        SELECT r.*,
               u1.nombre AS nombre_reportador, u1.email AS email_reportador,
               u2.nombre AS nombre_reportado, u2.email AS email_reportado,
               u2.estado AS estado_reportado, u2.rol AS rol_reportado,
               m.nombre AS marca, mo.nombre AS modelo
        FROM reportes r
        LEFT JOIN usuarios u1 ON COALESCE(r.id_reportador, r.id_usuario) = u1.id
        LEFT JOIN usuarios u2 ON r.id_reportado = u2.id
        LEFT JOIN vehiculos v ON r.id_vehiculo = v.id
        LEFT JOIN marcas m ON v.id_marca = m.id
        LEFT JOIN modelos mo ON v.id_modelo = mo.id
        WHERE 1=1
    """
    params = []
    
    if tipo_filter == 'usuarios':
        sql += " AND r.id_reportado IS NOT NULL AND u2.rol = 'comprador'"
    elif tipo_filter == 'vendedores':
        sql += " AND r.id_reportado IS NOT NULL AND u2.rol = 'vendedor'"
    elif tipo_filter == 'vehiculos':
        sql += " AND r.id_vehiculo IS NOT NULL"

    if estado_filter:
        sql += " AND r.estado = %s"
        params.append(estado_filter)
    if motivo_filter:
        sql += " AND r.motivo LIKE %s"
        params.append(f"%{motivo_filter}%")
    sql += " ORDER BY r.fecha DESC"

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql, params)
    reportes = cursor.fetchall()

    # Contadores para las tarjetas de métricas que sí respeten la categoría actual (tipo_filter)
    base_count_sql = """
        SELECT r.estado
        FROM reportes r
        LEFT JOIN usuarios u2 ON r.id_reportado = u2.id
        WHERE 1=1
    """
    if tipo_filter == 'usuarios':
        base_count_sql += " AND r.id_reportado IS NOT NULL AND u2.rol = 'comprador'"
    elif tipo_filter == 'vendedores':
        base_count_sql += " AND r.id_reportado IS NOT NULL AND u2.rol = 'vendedor'"
    elif tipo_filter == 'vehiculos':
        base_count_sql += " AND r.id_vehiculo IS NOT NULL"
        
    cursor.execute(base_count_sql)
    all_states = cursor.fetchall()
    
    total = len(all_states)
    pendientes = sum(1 for row in all_states if row['estado'] == 'pendiente')
    revisados = sum(1 for row in all_states if row['estado'] == 'revisado')
    cerrados = sum(1 for row in all_states if row['estado'] == 'cerrado')
    cursor.close()

    return render_template('admin/admin_reportes.html',
                           reportes=reportes,
                           total=total,
                           pendientes=pendientes,
                           revisados=revisados,
                           cerrados=cerrados,
                           estado_filter=estado_filter,
                           motivo_filter=motivo_filter)


@admin_bp.route('/reportes-usuarios/<int:id>')
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def ver_reporte_usuario(id):
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT r.*,
               u1.nombre AS nombre_reportador, u1.email AS email_reportador, u1.username AS username_reportador,
               u2.nombre AS nombre_reportado, u2.email AS email_reportado, u2.username AS username_reportado,
               u2.estado AS estado_reportado
        FROM reportes r
        LEFT JOIN usuarios u1 ON r.id_reportador = u1.id
        LEFT JOIN usuarios u2 ON r.id_reportado = u2.id
        WHERE r.id = %s
    """, (id,))
    reporte = cursor.fetchone()
    cursor.close()

    if not reporte:
        flash("Reporte no encontrado.", "danger")
        return redirect(url_for('admin.reportes_usuarios'))

    return render_template('admin/admin_reportes.html',
                           reporte_detalle=reporte,
                           reportes=[],
                           total=0, pendientes=0, revisados=0, cerrados=0,
                           estado_filter='', motivo_filter='')


@admin_bp.route('/reportes-usuarios/<int:id>/accion', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def accion_reporte(id):
    accion = request.form.get('accion')  # 'ban', 'advertencia', 'cerrar'
    nota = request.form.get('nota', '')

    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id_reportado, motivo FROM reportes WHERE id = %s", (id,))
    reporte = cursor.fetchone()

    if not reporte:
        cursor.close()
        flash("Reporte no encontrado.", "danger")
        return redirect(url_for('admin.reportes_usuarios'))

    id_reportado = reporte['id_reportado']
    motivo = reporte['motivo']

    try:
        titulo_notif = ""
        mensaje_notif = ""
        
        if accion == 'ban':
            cursor.execute("UPDATE usuarios SET estado='bloqueado' WHERE id=%s", (id_reportado,))
            cursor.execute("""UPDATE reportes SET estado='revisado', accion_tomada=%s WHERE id=%s""",
                           (f'Usuario baneado. Nota: {nota}', id))
            registrar_log('ban_usuario_por_reporte', 'usuario', id_reportado,
                          f'Baneado por reporte #{id}. Nota: {nota}')
            
            titulo_notif = "🚨 Cuenta Suspendida por Reporte"
            mensaje_notif = f"Hemos suspendido tu cuenta tras recibir y revisar un reporte por '{motivo}'. Si crees que se trata de un error o tienes dudas, por favor contacta a Soporte Técnico."
            
            flash(f"✅ Usuario baneado y reporte marcado como revisado.", "success")

        elif accion == 'advertencia':
            cursor.execute("""UPDATE reportes SET estado='revisado', accion_tomada=%s WHERE id=%s""",
                           (f'Advertencia enviada. Nota: {nota}', id))
            registrar_log('advertencia_por_reporte', 'reporte', id,
                          f'Advertencia al usuario #{id_reportado}. Nota: {nota}')
            
            titulo_notif = "⚠️ Advertencia de Moderación"
            mensaje_notif = f"Has recibido una advertencia debido a un reporte de otro usuario por '{motivo}'. Te sugerimos revisar las políticas de la comunidad. Si tienes alguna duda, contacta a Soporte Técnico."
            
            flash("⚠️ Advertencia registrada y reporte marcado como revisado.", "warning")

        elif accion == 'cerrar':
            cursor.execute("""UPDATE reportes SET estado='cerrado', accion_tomada=%s WHERE id=%s""",
                           (f'Cerrado sin acción. Nota: {nota}', id))
            registrar_log('cerrar_reporte', 'reporte', id,
                          f'Reporte #{id} cerrado sin acción. Nota: {nota}')
            flash("🔒 Reporte cerrado sin acciones adicionales.", "info")

        else:
            flash("Acción no válida.", "danger")

        # Insertar notificación si hubo acción disciplinaria
        if titulo_notif:
            try:
                cursor.execute("""
                    INSERT INTO notificaciones (id_usuario, tipo, titulo, mensaje, leida, fecha_creacion)
                    VALUES (%s, 'alerta', %s, %s, false, NOW())
                """, (id_reportado, titulo_notif, mensaje_notif))
            except Exception as e:
                print(f"⚠️ Aviso: No se pudo enviar notificación de reporte: {e}")

        conexion.commit()
    except Exception as e:
        conexion.rollback()
        flash(f"Error al procesar la acción: {e}", "danger")
        print(f"[REPORTE ERROR] {e}")
    finally:
        cursor.close()

    return redirect(url_for('admin.reportes_usuarios'))


@admin_bp.route('/reportes-usuarios/<int:id>/eliminar', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def eliminar_reporte_usuario(id):
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM reportes WHERE id = %s", (id,))
        conexion.commit()
        registrar_log('eliminar_reporte', 'reporte', id, f'Reporte #{id} eliminado')
        flash("🗑️ Reporte eliminado correctamente.", "success")
    except Exception as e:
        conexion.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    finally:
        cursor.close()
    return redirect(url_for('admin.reportes_usuarios'))


# ================================================================
#  EXPORTAR DATOS (CSV / PDF)
# ================================================================

@admin_bp.route('/exportar/<entidad>')
@login_activo_requerido
@admin_requerido
# exportar requiere cierto nivel elevado por seguridad, solo admin
@requiere_roles() 
def exportar_datos(entidad):
    import csv
    import io
    from flask import Response
    
    formato = request.args.get('formato', 'csv')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    if entidad not in ['usuarios', 'vehiculos', 'reportes', 'logs', 'vendedores']:
        flash("Entidad no válida para exportación.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = ""
    params = []
    
    # 1. Construir SQL según entidad
    if entidad == 'usuarios':
        sql = "SELECT id, nombre, apellidos, email, telefono, rol, estado, fecha_registro FROM usuarios WHERE 1=1"
        if fecha_inicio:
            sql += " AND DATE(fecha_registro) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(fecha_registro) <= %s"
            params.append(fecha_fin)
        sql += " ORDER BY id DESC"
            
    elif entidad == 'vehiculos':
        sql = """
            SELECT v.id, m.nombre AS marca, mo.nombre AS modelo, v.anio, 
                   v.precio, v.kilometraje, v.estado, v.fecha_publicacion, u.nombre AS vendedor 
            FROM vehiculos v
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            LEFT JOIN usuarios u ON v.id_usuario = u.id
            WHERE 1=1
        """
        if fecha_inicio:
            sql += " AND DATE(v.fecha_publicacion) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(v.fecha_publicacion) <= %s"
            params.append(fecha_fin)
        sql += " ORDER BY v.id DESC"
            
    elif entidad == 'reportes':
        sql = """
            SELECT r.id, r.titulo, r.detalle, r.estado, r.fecha,
                   u1.nombre AS reportador, u1.email AS email_reportador,
                   u2.nombre AS reportado, u2.email AS email_reportado,
                   m.nombre AS marca, mo.nombre AS modelo,
                   r.motivo, r.accion_tomada
            FROM reportes r
            LEFT JOIN usuarios u1 ON COALESCE(r.id_reportador, r.id_usuario) = u1.id
            LEFT JOIN usuarios u2 ON r.id_reportado = u2.id
            LEFT JOIN vehiculos v ON r.id_vehiculo = v.id
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE 1=1
        """
        if fecha_inicio:
            sql += " AND DATE(r.fecha) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(r.fecha) <= %s"
            params.append(fecha_fin)
        sql += " ORDER BY r.id DESC"
        
    elif entidad == 'logs':
        sql = "SELECT id, fecha, nombre_admin, accion, entidad, descripcion, ip FROM logs_admin WHERE 1=1"
        if fecha_inicio:
            sql += " AND DATE(fecha) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(fecha) <= %s"
            params.append(fecha_fin)
        sql += " ORDER BY id DESC"
        
    elif entidad == 'vendedores':
        sql = """
            SELECT pv.usuario_id, u.nombre, u.email, pv.nombre_tienda, 
                   pv.numero_id, pv.telefono_contacto, pv.direccion_negocio,
                   pv.estado_verificacion 
            FROM perfil_vendedor pv
            JOIN usuarios u ON pv.usuario_id = u.id
            WHERE 1=1
        """
        sql += " ORDER BY pv.id DESC"
        
    cursor.execute(sql, tuple(params))
    resultados = cursor.fetchall()
    cursor.close()
    
    # 2. Registrar en auditoría la acción de exportar
    registrar_log(f'exportar_{entidad}', entidad, 0, f'Exportación {formato.upper()}. Fechas: {fecha_inicio or "Todas"} a {fecha_fin or "Todas"}')
    
    if not resultados:
        flash(f"No hay datos de '{entidad}' en ese rango para exportar.", "warning")
        return redirect(request.referrer or url_for('admin.dashboard'))
    
    # 3. Generar CSV
    if formato == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir cabeceras
        writer.writerow(resultados[0].keys())
        # Escribir filas
        for fila in resultados:
            writer.writerow(fila.values())
            
        # Añadir BOM para que Excel lea UTF-8 correctamente
        csv_data = "\ufeff" + output.getvalue()
        
        response = Response(csv_data, mimetype='text/csv; charset=utf-8')
        response.headers['Content-Disposition'] = f'attachment; filename=exportacion_{entidad}.csv'
        return response
        
    # 4. Vista de Impresión (PDF visual)
    elif formato == 'pdf' or formato == 'imprimir':
        return render_template('admin/admin_imprimir.html', 
                               entidad=entidad.capitalize(), 
                               datos=resultados, 
                               fecha_inicio=fecha_inicio, 
                               fecha_fin=fecha_fin)
                               
    flash("Formato no soportado.", "danger")
    return redirect(request.referrer or url_for('admin.dashboard'))

# ================================================================
#  LOGS DE AUDITORÍA
# ================================================================

@admin_bp.route('/logs')
@login_activo_requerido
@admin_requerido
def logs_auditoria():
    admin_filter  = request.args.get('admin', '').strip()
    accion_filter = request.args.get('accion', '').strip()
    fecha_desde   = request.args.get('fecha_desde', '').strip()
    fecha_hasta   = request.args.get('fecha_hasta', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    sql = "SELECT * FROM logs_admin WHERE 1=1"
    params = []

    if admin_filter:
        sql += " AND (nombre_admin LIKE %s OR id_admin = %s)"
        params.extend([f"%{admin_filter}%", admin_filter if admin_filter.isdigit() else -1])
    if accion_filter:
        sql += " AND accion LIKE %s"
        params.append(f"%{accion_filter}%")
    if fecha_desde:
        sql += " AND fecha >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += " AND fecha <= %s"
        params.append(f"{fecha_hasta} 23:59:59")

    # Total para paginación
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) AS c")
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(count_sql, params)
    total_logs = cursor.fetchone()['c']

    sql += " ORDER BY fecha DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    cursor.execute(sql, params)
    logs = cursor.fetchall()
    cursor.close()

    total_pages = (total_logs + per_page - 1) // per_page

    return render_template('admin/admin_logs.html',
                           logs=logs,
                           total_logs=total_logs,
                           page=page,
                           total_pages=total_pages,
                           admin_filter=admin_filter,
                           accion_filter=accion_filter,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)

# ====================================================
# ACCIONES MASIVAS (BULK ACTIONS)
# ====================================================

@admin_bp.route('/usuarios/bulk', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def usuarios_bulk():
    data = request.json
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    accion = data.get('accion')
    
    if not ids or not accion:
        return jsonify({'success': False, 'message': 'Faltan datos para la operación.'}), 400
        
    cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    soy_superadmin = (session.get('rol') == 'superadmin')
    procesados = 0
    omitidos = 0
    
    try:
        # 1. Obtener información de los usuarios a afectar
        format_ids = ','.join(['%s'] * len(ids))
        cursor.execute(f"SELECT id, rol, username FROM usuarios WHERE id IN ({format_ids})", tuple(ids))
        usuarios_afectados = cursor.fetchall()
        
        ids_validos = []
        for u in usuarios_afectados:
            # Protección SUPERADMIN: solo otro superadmin puede tocarlos
            if u['rol'] == 'superadmin' and not soy_superadmin:
                omitidos += 1
                continue
            ids_validos.append(u['id'])
            
        if not ids_validos:
            return jsonify({'success': False, 'message': 'No se pueden procesar estas cuentas debido a restricciones de nivel.'}), 403
            
        final_ids = tuple(ids_validos)
        format_final = ','.join(['%s'] * len(ids_validos))
        
        if accion == 'bloquear':
            cursor.execute(f"UPDATE usuarios SET estado = 'bloqueado' WHERE id IN ({format_final})", final_ids)
            procesados = cursor.rowcount
            registrar_log('bulk_bloquear_usuarios', 'usuario', None, f'Bloqueo masivo de {procesados} usuarios')
            
            # Notificaciones por Email
            try:
                cursor.execute(f"SELECT email, nombre FROM usuarios WHERE id IN ({format_final})", final_ids)
                for u in cursor.fetchall():
                    if u['email']:
                        html_prem = generar_html_email('alert', {
                            'titulo': 'Tu cuenta ha sido restringida',
                            'mensaje': f"Hola <strong>{u['nombre'] or 'Usuario'}</strong>, te informamos que tras una revisión administrativa, tu cuenta en Drive Market ha sido suspendida temporalmente.",
                            'datos_clave': [{'label': 'Estado', 'value': 'Suspendido / Bloqueado'}],
                            'boton_texto': 'Contactar Soporte',
                            'boton_url': url_for('sobrenosotros', _external=True)
                        })
                        enviar_notificacion_email(u['email'], "⚠️ Aviso de Suspensión de Cuenta", html_prem)
            except Exception as e_mail: print(f"Error email: {e_mail}")
            
        elif accion == 'desbloquear':
            cursor.execute(f"UPDATE usuarios SET estado = 'activo' WHERE id IN ({format_final})", final_ids)
            procesados = cursor.rowcount
            registrar_log('bulk_desbloquear_usuarios', 'usuario', None, f'Desbloqueo masivo de {procesados} usuarios')
            
            # Notificaciones por Email
            try:
                cursor.execute(f"SELECT email, nombre FROM usuarios WHERE id IN ({format_final})", final_ids)
                for u in cursor.fetchall():
                    if u['email']:
                        html_prem = generar_html_email('success', {
                            'titulo': '¡Tu cuenta ha sido reactivada!',
                            'mensaje': f"Hola <strong>{u['nombre'] or 'Usuario'}</strong>, nos alegra informarte que tu cuenta ha sido restablecida. Ya puedes disfrutar de todos nuestros servicios.",
                            'datos_clave': [{'label': 'Acceso', 'value': 'Habilitado'}],
                            'boton_texto': 'Ir a mi Cuenta',
                            'boton_url': url_for('login', _external=True)
                        })
                        enviar_notificacion_email(u['email'], "✅ Tu cuenta ha sido reactivada", html_prem)
            except Exception as e_mail: print(f"Error email: {e_mail}")
            
        elif accion == 'eliminar':
            # Según requerimiento del usuario "que se borren también" (vehículos asociados)
            # Primero borramos vehículos para evitar errores de integridad
            cursor.execute(f"DELETE FROM vehiculos WHERE id_usuario IN ({format_final})", final_ids)
            num_vehiculos = cursor.rowcount
            
            # Ahora borramos los usuarios
            cursor.execute(f"DELETE FROM usuarios WHERE id IN ({format_final})", final_ids)
            procesados = cursor.rowcount
            registrar_log('bulk_eliminar_usuarios', 'usuario', None, f'Eliminación masiva de {procesados} usuarios y {num_vehiculos} vehículos')
        
        conexion.commit()
        
        msg = f"Operación completada: {procesados} procesados."
        if omitidos > 0:
            msg += f" ({omitidos} omitidos por seguridad)."
            
        return jsonify({'success': True, 'message': msg})
        
    except Exception as e:
        conexion.rollback()
        print(f"Error en usuarios_bulk: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor.'}), 500
    finally:
        cursor.close()

@admin_bp.route('/vehiculos/bulk', methods=['POST'])
@login_activo_requerido
@admin_requerido
@requiere_roles('moderador')
def vehiculos_bulk():
    data = request.json
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    accion = data.get('accion')
    
    if not ids or not accion:
        return jsonify({'success': False, 'message': 'Faltan datos.'}), 400
        
    cursor = conexion.cursor()
    try:
        ids_tuple = tuple(ids)
        format_ids = ','.join(['%s'] * len(ids))
        
        if accion == 'activar':
            cursor.execute(f"UPDATE vehiculos SET estado = 'activo' WHERE id IN ({format_ids})", ids_tuple)
        elif accion == 'bloquear':
            cursor.execute(f"UPDATE vehiculos SET estado = 'bloqueado' WHERE id IN ({format_ids})", ids_tuple)
        elif accion == 'eliminar':
            cursor.execute(f"DELETE FROM vehiculos WHERE id IN ({format_ids})", ids_tuple)
            
        procesados = cursor.rowcount
        
        # Notificaciones por Email (solo para bloqueo)
        if accion == 'bloquear':
            try:
                # Obtener emails de los dueños de los vehículos
                cursor.execute(f"""
                    SELECT DISTINCT u.email, u.nombre, v.id as vid, m.nombre as marca, mo.nombre as modelo
                    FROM vehiculos v
                    JOIN usuarios u ON v.id_usuario = u.id
                    LEFT JOIN marcas m ON v.id_marca = m.id
                    LEFT JOIN modelos mo ON v.id_modelo = mo.id
                    WHERE v.id IN ({format_ids})
                """, ids_tuple)
                for v in cursor.fetchall():
                    if v['email']:
                        html_prem = generar_html_email('warning', {
                            'titulo': 'Aviso de Moderación de Vehículo',
                            'mensaje': f"Hola <strong>{v['nombre'] or 'Usuario'}</strong>, tu anuncio ha sido retirado temporalmente para una revisión de calidad.",
                            'datos_clave': [
                                {'label': 'Vehículo', 'value': f"{v['marca']} {v['modelo']}"},
                                {'label': 'Publicación ID', 'value': str(v['vid'])}
                            ],
                            'boton_texto': 'Ir a mis Vehículos',
                            'boton_url': url_for('vendedor.mis_vehiculos', _external=True)
                        })
                        enviar_notificacion_email(v['email'], "📌 Aviso de Moderación de Vehículo", html_prem)
            except Exception as e_mail: print(f"Error email veh: {e_mail}")

        conexion.commit()
        
        registrar_log(f'bulk_{accion}_vehiculos', 'vehiculo', None, f'Acción {accion} en {procesados} vehículos')
        
        return jsonify({'success': True, 'message': f'Se han procesado {procesados} vehículos correctamente.'})
        
    except Exception as e:
        conexion.rollback()
        print(f"Error en vehiculos_bulk: {e}")
        return jsonify({'success': False, 'message': 'Error al procesar la solicitud.'}), 500
    finally:
        cursor.close()

# ---------------------------------------------------------------
#  GESTIÓN DE PAGOS MANUALES (ANUNCIOS DESTACADOS)
# ---------------------------------------------------------------

@admin_bp.route('/pagos')
@login_activo_requerido
@admin_requerido
def admin_pagos():
    """Lista todos los pagos pendientes de revisión"""
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT v.id, v.id_usuario, v.comprobante_pago, v.estado_pago, v.fecha_publicacion,
                   m.nombre AS marca, mo.nombre AS modelo, u.nombre AS usuario_nombre, u.email
            FROM vehiculos v
            JOIN usuarios u ON v.id_usuario = u.id
            LEFT JOIN marcas m ON v.id_marca = m.id
            LEFT JOIN modelos mo ON v.id_modelo = mo.id
            WHERE v.estado_pago = 'pendiente'
            ORDER BY v.id DESC
        """)
        pagos_pendientes = cursor.fetchall()
        cursor.close()
        return render_template('admin/pagos.html', pagos=pagos_pendientes)
    except Exception as e:
        print(f"Error cargando pagos: {e}")
        flash("Error al cargar la lista de pagos.", "error")
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/pagos/aprobar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
def aprobar_pago(id):
    """Aprueba un pago, destacando el vehículo por 30 días"""
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE vehiculos 
            SET estado_pago = 'aprobado', 
                plan_destacado = TRUE,
                fecha_fin_destacado = NOW() + INTERVAL '30 days'
            WHERE id = %s
        """, (id,))
        conexion.commit()
        cursor.close()
        flash("Pago aprobado. El anuncio ahora es destacado por 30 días.", "success")
    except Exception as e:
        print(f"Error aprobando pago: {e}")
        conexion.rollback()
        flash("Error al aprobar el pago.", "error")
        
    return redirect(url_for('admin.admin_pagos'))

@admin_bp.route('/pagos/rechazar/<int:id>', methods=['POST'])
@login_activo_requerido
@admin_requerido
def rechazar_pago(id):
    """Rechaza un pago"""
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE vehiculos 
            SET estado_pago = 'rechazado', 
                plan_destacado = FALSE
            WHERE id = %s
        """, (id,))
        conexion.commit()
        cursor.close()
        flash("Pago rechazado.", "warning")
    except Exception as e:
        print(f"Error rechazando pago: {e}")
        conexion.rollback()
        flash("Error al rechazar el pago.", "error")
        
    return redirect(url_for('admin.admin_pagos'))

