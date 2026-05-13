# supabase_example.py
# Ejemplos de uso de Supabase en Drivemarket

from flask import Blueprint, jsonify
from Drivemarket.supabase_config import supabase_api, supabase_db
import requests

# Blueprint para rutas de Supabase (ejemplo)
supabase_bp = Blueprint('supabase', __name__, url_prefix='/api/supabase')

# ---------------------------------------------------------------
# OPCIÓN 1: Usar API REST de Supabase
# ---------------------------------------------------------------

@supabase_bp.route('/test-rest', methods=['GET'])
def test_supabase_rest():
    """Test de conexión a Supabase REST API"""
    if not supabase_api.is_configured():
        return jsonify({"error": "Supabase no está configurada"}), 400
    
    try:
        # Ejemplo: consultar tabla 'users'
        headers = {
            "Authorization": f"Bearer {supabase_api.key}",
            "Content-Type": "application/json"
        }
        
        url = f"{supabase_api.url}/rest/v1/users?select=*"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return jsonify({
                "status": "✅ Conectado a Supabase REST",
                "users_count": len(response.json())
            })
        else:
            return jsonify({
                "error": response.text
            }), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------
# OPCIÓN 2: Usar PostgreSQL directo de Supabase
# ---------------------------------------------------------------

@supabase_bp.route('/test-postgres', methods=['GET'])
def test_supabase_postgres():
    """Test de conexión a Supabase PostgreSQL"""
    try:
        conn = supabase_db
        cursor = conn.cursor()
        
        # Ejecutar consulta simple
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        cursor.close()
        
        return jsonify({
            "status": "✅ Conectado a Supabase PostgreSQL",
            "version": version[0] if version else "Desconocida"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------
# EJEMPLO: Obtener datos de tabla en Supabase
# ---------------------------------------------------------------

@supabase_bp.route('/usuarios', methods=['GET'])
def get_usuarios_supabase():
    """Obtener usuarios desde Supabase"""
    try:
        conn = supabase_db
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nombre, email FROM users LIMIT 10;")
        usuarios = cursor.fetchall()
        
        cursor.close()
        
        return jsonify({
            "usuarios": [
                {"id": u[0], "nombre": u[1], "email": u[2]}
                for u in usuarios
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Para usar este blueprint en app.py:
# from Drivemarket.supabase_example import supabase_bp
# app.register_blueprint(supabase_bp)
