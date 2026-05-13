# supabase_config.py
# Configuración de Supabase para Drivemarket

import os
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

# ---------------------------------------------------------------
# 📊 CONEXIÓN A SUPABASE (API REST)
# ---------------------------------------------------------------

class SupabaseAPI:
    """Cliente para Supabase REST API"""
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
    def is_configured(self):
        return self.url and self.key and "[REEMPLAZA" not in self.key

    def __repr__(self):
        return f"<SupabaseAPI: {self.url if self.is_configured() else 'NO CONFIGURADO'}>"

# ---------------------------------------------------------------
# 🗄️ CONEXIÓN A SUPABASE (PostgreSQL directo)
# ---------------------------------------------------------------

_supabase_conexion = None

def get_supabase_db():
    """Retorna una conexión a PostgreSQL de Supabase"""
    global _supabase_conexion
    
    try:
        # Opción 1: Usar credenciales específicas de Supabase
        host = os.getenv("SUPABASE_DB_HOST", "saextawaeybnbclqeonl.supabase.co")
        user = os.getenv("SUPABASE_DB_USER", "postgres")
        password = os.getenv("SUPABASE_DB_PASSWORD", "[REEMPLAZA_CON_PASSWORD]")
        dbname = os.getenv("SUPABASE_DB_NAME", "postgres")
        port = int(os.getenv("SUPABASE_DB_PORT", "5432"))
        
        if "[REEMPLAZA" in password:
            print("⚠️  Supabase PostgreSQL no configurada aún. Configura las credenciales en .env")
            return None
        
        if _supabase_conexion is None or (hasattr(_supabase_conexion, 'closed') and _supabase_conexion.closed):
            _supabase_conexion = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                dbname=dbname,
                port=port,
                sslmode='require'  # Supabase requiere SSL
            )
            _supabase_conexion.autocommit = False
            print("✅ Conectado a Supabase PostgreSQL")
    except (psycopg2.InterfaceError, psycopg2.OperationalError, Exception) as e:
        print(f"❌ Error conectando a Supabase: {e}")
        _supabase_conexion = None
        
    return _supabase_conexion

class SupabaseDBProxy:
    """Proxy para conexión PostgreSQL de Supabase"""
    def __getattr__(self, name):
        conn = get_supabase_db()
        if conn is None:
            raise psycopg2.OperationalError("No se pudo conectar a Supabase PostgreSQL")
        return getattr(conn, name)

# Instancia de API REST
supabase_api = SupabaseAPI()

# Proxy para conexión PostgreSQL
supabase_db = SupabaseDBProxy()

# Verificar configuración
if __name__ == "__main__":
    print("\n📋 Estado de Configuración Supabase:")
    print(f"  API REST: {'✅ Configurada' if supabase_api.is_configured() else '❌ No configurada'}")
    print(f"  URL: {supabase_api.url if supabase_api.url else 'No definida'}")
    print("\n  Para completar la configuración:")
    print("  1. Ve a tu dashboard de Supabase")
    print("  2. Settings > API > copia 'anon public key'")
    print("  3. Pega en .env como SUPABASE_KEY=...")
