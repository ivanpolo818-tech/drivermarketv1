# comparador_routes.py - Rutas para Comparador de Vehículos
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import text
from models import db
from helpers.asistente_ia import generar_analisis_comparativo_ai

# Crear blueprint
comparador_bp = Blueprint('comparador', __name__)

# NOTE: This module requires the real `vehiculos` table in the configured
# database. There is no local fallback; any DB errors will return HTTP 500.

@comparador_bp.route('/comparador')
def comparador():
    """Página del comparador de vehículos"""
    from flask import request
    vehiculo_id = request.args.get('vehiculo_id', type=int)
    return render_template('base/comparador.html', vehiculo_id_inicial=vehiculo_id)

@comparador_bp.route('/api/comparador/vehiculos')
def get_vehiculos_comparador():
    """Obtiene todos los vehículos para el comparador"""
    try:
        # Adjusted to actual DB columns: id_marca, id_modelo, kilometraje, ciudad_venta
        # Join marcas and modelos to return readable names
        sql = text(
            "SELECT v.id, m.nombre AS marca, mo.nombre AS modelo, v.version, v.anio, v.precio, v.kilometraje, v.negociable, v.ciudad_venta, v.slug, "
            "v.transmision, v.combustible, v.motor AS cilindraje, v.puertas, "
            "tp.nombre AS tipo, "
            "COALESCE((SELECT iv.url_imagen FROM imagenes_vehiculos iv WHERE iv.id_vehiculo = v.id ORDER BY iv.id ASC LIMIT 1), v.imagen) AS imagen "
            "FROM vehiculos v "
            "LEFT JOIN marcas m ON v.id_marca = m.id "
            "LEFT JOIN modelos mo ON v.id_modelo = mo.id "
            "LEFT JOIN tipos_vehiculos tp ON v.id_tipo = tp.id "
            "LIMIT 100"
        )
        res = db.session.execute(sql)
        rows = res.mappings().all()
        vehiculos_db = []
        if rows:
            for r in rows:
                item = dict(r)
                # Normalizar tipos para JSON
                if 'precio' in item and item['precio'] is not None:
                    try:
                        item['precio'] = float(item['precio'])
                    except Exception:
                        item['precio'] = None
                else:
                    item['precio'] = None

                if 'kilometraje' in item:
                    try:
                        item['kilometraje'] = int(item['kilometraje'] or 0)
                    except Exception:
                        item['kilometraje'] = 0
                else:
                    item['kilometraje'] = 0

                # image fallback
                if not item.get('imagen'):
                    item['imagen'] = 'img/default_car.jpg'
                
                # Asegurar que el slug exista para los links
                if not item.get('slug'):
                    item['slug'] = str(item['id'])

                vehiculos_db.append(item)

        return jsonify(vehiculos_db)
    except Exception as e:
        print(f"❌ Error al consultar vehiculos: {e}")
        return jsonify({'error': 'Error al consultar la base de datos', 'details': str(e)}), 500

@comparador_bp.route('/api/comparador/detalles/<int:vehiculo_id>')
def get_detalles_vehiculo(vehiculo_id):
    """Obtiene detalles completos de un vehículo"""
    try:
        sql = text(
            "SELECT v.*, m.nombre AS marca, mo.nombre AS modelo, tp.nombre AS tipo, v.motor AS cilindraje "
            "FROM vehiculos v "
            "LEFT JOIN marcas m ON v.id_marca = m.id "
            "LEFT JOIN modelos mo ON v.id_modelo = mo.id "
            "LEFT JOIN tipos_vehiculos tp ON v.id_tipo = tp.id "
            "WHERE v.id = :id"
        )
        res = db.session.execute(sql, {"id": vehiculo_id})
        row = res.mappings().first()
        if row:
            return jsonify(dict(row))
        return jsonify({'error': 'Vehículo no encontrado'}), 404
    except Exception as e:
        print(f"❌ Error al obtener detalles de vehiculo {vehiculo_id}: {e}")
        return jsonify({'error': 'Error al consultar la base de datos', 'details': str(e)}), 500

@comparador_bp.route('/api/comparador/analisis', methods=['POST'])
def analisis_comparador():
    """Análisis inteligente de comparación"""
    try:
        datos = request.json
        vehiculo_ids = datos.get('vehiculo_ids', [])
        
        # Obtener detalles de vehículos
        vehiculos_comparar = []
        
        # Intentar obtener datos desde la DB mediante SQLAlchemy
        try:
            for vid in vehiculo_ids:
                sql = text(
                    "SELECT v.*, m.nombre AS marca, mo.nombre AS modelo, tp.nombre AS tipo, v.motor AS cilindraje "
                    "FROM vehiculos v "
                    "LEFT JOIN marcas m ON v.id_marca = m.id "
                    "LEFT JOIN modelos mo ON v.id_modelo = mo.id "
                    "LEFT JOIN tipos_vehiculos tp ON v.id_tipo = tp.id "
                    "WHERE v.id = :id"
                )
                res = db.session.execute(sql, {"id": vid})
                row = res.mappings().first()
                if row:
                    item = dict(row)
                    # Normalizar tipos
                    if 'precio' in item and item['precio'] is not None:
                        try:
                            item['precio'] = float(item['precio'])
                        except Exception:
                            item['precio'] = None
                    vehiculos_comparar.append(item)
        except Exception as e:
            print(f"❌ Error al obtener datos para analisis: {e}")
            return jsonify({'error': 'Error al consultar la base de datos', 'details': str(e)}), 500

        if not vehiculos_comparar:
            return jsonify({'error': 'No hay vehículos para comparar (IDs no encontrados en DB)'}), 400
        
        # Análisis: mejor precio/km, mejor valor general
        # Normalize keys: use 'kilometraje' and ensure precio numeric
        for v in vehiculos_comparar:
            if 'precio' in v:
                try:
                    v['_precio_float'] = float(v['precio'])
                except Exception:
                    v['_precio_float'] = float(0)
            else:
                v['_precio_float'] = 0.0
            v['_km'] = v.get('kilometraje', v.get('km', 0) or 0)

        analisis = {
            'mejor_precio': min(vehiculos_comparar, key=lambda x: x['_precio_float']),
            'menor_km': min(vehiculos_comparar, key=lambda x: x['_km']),
            'mejor_relacion': min(vehiculos_comparar, key=lambda x: x['_precio_float'] / (x['_km'] + 1)),
            'total_vehiculos': len(vehiculos_comparar),
            'recomendacion': f"De los {len(vehiculos_comparar)} vehículos, se ha calculado el análisis."
        }
        
        return jsonify(analisis)
    except Exception as e:
        print(f"❌ Error en análisis: {e}")
        return jsonify({'error': str(e)}), 500

@comparador_bp.route('/api/comparador/analizar-ia', methods=['POST'])
def analizar_ia_endpoint():
    """Endpoint para análisis comparativo con IA"""
    try:
        data = request.json
        vehiculo_ids = data.get('vehiculo_ids', [])
        
        if not vehiculo_ids or len(vehiculo_ids) < 2:
            return jsonify({'error': 'Selecciona al menos 2 vehículos para que la IA los analice.'}), 400

        # Obtener detalles completos para la IA
        vehiculos_datos = []
        for vid in vehiculo_ids:
            # Query for the AI detail
            sql = text(
                "SELECT v.*, m.nombre AS marca, mo.nombre AS modelo "
                "FROM vehiculos v "
                "LEFT JOIN marcas m ON v.id_marca = m.id "
                "LEFT JOIN modelos mo ON v.id_modelo = mo.id "
                "WHERE v.id = :id"
            )
            res = db.session.execute(sql, {"id": vid})
            row = res.mappings().first()
            if row:
                item = dict(row)
                # Ensuring numeric price
                try: item['precio'] = float(item.get('precio', 0) or 0)
                except: item['precio'] = 0.0
                
                # Use engine column if needed for AI prompt
                item['cilindraje'] = item.get('motor', 'N/D')
                vehiculos_datos.append(item)

        if not vehiculos_datos:
            return jsonify({'error': 'No pudimos encontrar los datos de los vehículos seleccionados.'}), 404

        # Llamar a la IA
        analisis, tipo = generar_analisis_comparativo_ai(vehiculos_datos)
        
        return jsonify({
            'analisis': analisis,
            'tipo': tipo
        })

    except Exception as e:
        print(f"❌ Error en analizar_ia_endpoint: {e}")
        return jsonify({'error': str(e)}), 500

