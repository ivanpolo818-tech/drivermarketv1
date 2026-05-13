# db_config.py

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------
# ⚙️ GESTIÓN CENTRALIZADA DE BASE DE DATOS (PostgreSQL)
# ---------------------------------------------------------------
_conexion_real = None

def get_db():
    """Retorna una conexión activa al servidor, reconectando si es necesario."""
    global _conexion_real
    
    try:
        # Si la conexión no existe o está cerrada, intentar reconectar
        if _conexion_real is None or (hasattr(_conexion_real, 'closed') and _conexion_real.closed):
            host = os.getenv("DB_HOST", "localhost")
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "samueladso")
            dbname = os.getenv("DB_NAME", "todoen1unos")
            port = int(os.getenv("DB_PORT", "5432"))
            _conexion_real = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                dbname=dbname,
                port=port
            )
            _conexion_real.autocommit = False
    except (psycopg2.InterfaceError, psycopg2.OperationalError, Exception) as e:
        print("❌ [db_config] Error reconectando a PostgreSQL:", e)
        _conexion_real = None
        
    return _conexion_real

class DBProxy:
    """Objeto Proxy que redirige todas las llamadas a la conexión real actual."""
    def __getattr__(self, name):
        conn = get_db()
        if conn is None:
            raise psycopg2.OperationalError("No se pudo establecer conexión con la base de datos.")
        return getattr(conn, name)

# Esta es la variable que todos los módulos importan
conexion = DBProxy()

# Inicialización primaria
get_db()

