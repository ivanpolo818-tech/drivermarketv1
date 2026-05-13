import psycopg2.extras
from db_config import conexion

def get_market_average(id_marca, id_modelo, anio, exclusion_id=None):
    """
    Calcula el precio promedio de mercado para un Marca/Modelo/Año específico.
    Excluye el vehículo actual si se proporciona un exclusion_id.
    """
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT AVG(precio) as promedio, COUNT(*) as muestra
            FROM vehiculos
            WHERE id_marca = %s AND id_modelo = %s AND anio BETWEEN %s AND %s
            AND estado = 'activo'
        """
        params = [id_marca, id_modelo, anio - 2, anio + 2]
        
        if exclusion_id:
            query += " AND id != %s"
            params.append(exclusion_id)
            
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()
        cursor.close()
        
        if result and result['promedio']:
            return {
                'promedio': float(result['promedio']),
                'muestra': result['muestra']
            }
        return None
    except Exception as e:
        print(f"Error calculating market average: {e}")
        if conexion:
            conexion.rollback()
        return None

def toggle_featured(vehicle_id, active=True):
    """Activa o desactiva el estado destacado de un vehículo."""
    try:
        cursor = conexion.cursor()
        if active:
            cursor.execute("""
                UPDATE vehiculos 
                SET es_destacado = TRUE, fecha_destacado = NOW() 
                WHERE id = %s
            """, (vehicle_id,))
        else:
            cursor.execute("""
                UPDATE vehiculos 
                SET es_destacado = FALSE, fecha_destacado = NULL 
                WHERE id = %s
            """, (vehicle_id,))
        conexion.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error toggling featured status: {e}")
        conexion.rollback()
        return False

