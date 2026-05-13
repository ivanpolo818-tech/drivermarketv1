"""
Módulo de funciones auxiliares para notificaciones (CORREGIDO)
"""

import psycopg2
import psycopg2.extras
from datetime import datetime

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="samueladso",
        dbname="todoen1unos",
        port=5432
    )
    conn.autocommit = False
    return conn

# Función global para el envío de correos (se asigna desde app.py)
enviar_correo_global = None

def crear_notificacion_general(id_usuario, tipo, titulo, mensaje, url_accion=None, id_relacion=None, critico=False):
    """
    Crea una notificación en la base de datos y opcionalmente envía email según preferencias (Opción B)
    """
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # 1. Insertar en la campanita de la web (SIEMPRE)
        cursor.execute("""
            INSERT INTO notificaciones 
            (id_usuario, tipo, titulo, mensaje, url_accion, id_relacion, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING id
        """, (id_usuario, tipo, titulo, mensaje, url_accion, id_relacion))
        
        notif_id = cursor.fetchone()['id']
        db.commit()

        # 2. LÓGICA DE PREFERENCIAS (EMAIL)
        mapeo = {
            'mensaje_nuevo': 'notif_mensajes',
            'precio_bajo': 'notif_precio',
            'oferta_nueva': 'notif_ofertas',
            'favorito': 'notif_favoritos',
            'sistema': 'notif_updates'
        }

        enviar_email_ya = critico # Si es crítico (2FA, Bloqueo), se envía siempre

        if not enviar_email_ya and tipo in mapeo:
            columna = mapeo[tipo]
            cursor.execute(f"SELECT {columna} FROM preferencias_usuario WHERE usuario_id = %s", (id_usuario,))
            preferencia = cursor.fetchone()
            
            # Valores por defecto si no hay registro
            default_pref = True if tipo in ['mensaje_nuevo', 'oferta_nueva'] else False
            enviar_email_ya = preferencia[columna] if preferencia is not None else default_pref

        # 3. Disparar email si la preferencia es positiva
        if enviar_email_ya and enviar_correo_global:
            cursor.execute("SELECT nombre, email FROM usuarios WHERE id = %s", (id_usuario,))
            user_data = cursor.fetchone()
            if user_data and user_data['email']:
                try:
                    # El objeto enviar_correo_global debe manejar el renderizado con plantillas Premium
                    enviar_correo_global(
                        notif_id=notif_id,
                        email_destino=user_data['email'],
                        nombre_usuario=user_data['nombre'],
                        tipo=tipo,
                        titulo=titulo,
                        mensaje=mensaje,
                        url_accion=url_accion
                    )
                except Exception as ex:
                    print(f"⚠ Error al disparar email automático: {ex}")

        return notif_id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear notificación: {e}")
        return None
        
    finally:
        cursor.close()
        db.close()

def notificar_precio_bajo(id_vehiculo, precio_actual, precio_anterior):
    """
    Notifica a todos los usuarios que tienen alerta cuando baja el precio
    """
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Obtener usuarios con alerta para este vehículo
        cursor.execute("""
            SELECT a.id_usuario, u.nombre as usuario_nombre, u.email as usuario_email,
                   m.nombre as marca, mo.nombre as modelo
            FROM alertas_precio a
            JOIN vehiculos v ON a.id_vehiculo = v.id
            JOIN marcas m ON v.id_marca = m.id
            JOIN modelos mo ON v.id_modelo = mo.id
            JOIN usuarios u ON a.id_usuario = u.id
            WHERE a.id_vehiculo = %s 
              AND a.precio_referencia > %s
              AND a.notificado = FALSE
        """, (id_vehiculo, precio_actual))
        
        usuarios = cursor.fetchall()
        
        for usuario in usuarios:
            mensaje = f'La publicación {usuario["marca"]} {usuario["modelo"]} ha registrado un descenso de precio: de ${precio_anterior:,.0f} a ${precio_actual:,.0f}'
            
            crear_notificacion_general(
                id_usuario=usuario['id_usuario'],
                tipo='precio_bajo',
                titulo='Actualización de Precio',
                mensaje=mensaje,
                url_accion=f'/detalle/{id_vehiculo}',
                id_relacion=id_vehiculo
            )
            
            # Marcar alerta como notificada
            cursor.execute("""
                UPDATE alertas_precio 
                SET notificado = TRUE, fecha_notificacion = NOW()
                WHERE id_usuario = %s AND id_vehiculo = %s
            """, (usuario['id_usuario'], id_vehiculo))
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al notificar precio bajo: {e}")
        
    finally:
        cursor.close()
        db.close()

def notificar_nuevo_mensaje(id_usuario_destino, id_usuario_remitente, id_vehiculo, mensaje_texto):
    """
    Notifica a un usuario que recibió un nuevo mensaje
    """
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Obtener datos del remitente y vehículo
        cursor.execute("""
            SELECT u.nombre as remitente_nombre,
                   m.nombre as marca, mo.nombre as modelo
            FROM usuarios u
            JOIN vehiculos v ON %s = v.id
            JOIN marcas m ON v.id_marca = m.id
            JOIN modelos mo ON v.id_modelo = mo.id
            WHERE u.id = %s
        """, (id_vehiculo, id_usuario_remitente))
        
        datos = cursor.fetchone()
        
        if datos:
            mensaje_corto = mensaje_texto[:100] + ('...' if len(mensaje_texto) > 100 else '')
            mensaje = f'El usuario {datos["remitente_nombre"]} ha enviado una nueva comunicación respecto al vehículo {datos["marca"]} {datos["modelo"]}: "{mensaje_corto}"'
            
            crear_notificacion_general(
                id_usuario=id_usuario_destino,
                tipo='mensaje_nuevo',
                titulo='Nuevo Mensaje',
                mensaje=mensaje,
                url_accion=f'/mensajes/chat/{id_vehiculo}?usuario={id_usuario_remitente}',
                id_relacion=id_vehiculo
            )
            
    except Exception as e:
        print(f"❌ Error al notificar nuevo mensaje: {e}")
        
    finally:
        cursor.close()
        db.close()

def obtener_notificaciones_no_leidas(id_usuario, solo_conteo=False):
    """
    Obtiene las notificaciones no leídas de un usuario o el conteo total.
    """
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        if solo_conteo:
            cursor.execute("SELECT COUNT(*) as total FROM notificaciones WHERE id_usuario = %s AND leida = FALSE", (id_usuario,))
            result = cursor.fetchone()
            return result['total'] if result else 0
            
        cursor.execute("""
            SELECT n.*, 
                   CASE 
                       WHEN EXTRACT(EPOCH FROM (NOW() - n.fecha_creacion))/3600 < 1 
                            THEN CAST(EXTRACT(EPOCH FROM (NOW() - n.fecha_creacion))/60 AS INTEGER) || ' min'
                       WHEN EXTRACT(EPOCH FROM (NOW() - n.fecha_creacion))/86400 < 1 
                            THEN CAST(EXTRACT(EPOCH FROM (NOW() - n.fecha_creacion))/3600 AS INTEGER) || ' h'
                       ELSE TO_CHAR(n.fecha_creacion, 'DD/MM')
                   END as tiempo_transcurrido
            FROM notificaciones n
            WHERE n.id_usuario = %s AND n.leida = FALSE
            ORDER BY n.fecha_creacion DESC
            LIMIT 10
        """, (id_usuario,))
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"❌ Error al obtener notificaciones no leídas: {e}")
        return 0 if solo_conteo else []
        
    finally:
        cursor.close()
        db.close()
