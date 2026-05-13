#!/usr/bin/env python3
"""
Script de migración: Agregar columna destacada a la tabla marcas
"""

import sys
import os

sys.path.insert(0, r'c:\Users\ASUS\OneDrive\Documentos\Proyect')

try:
    from Drivemarket.db_config import get_db
    import psycopg2
    import psycopg2.extras
    
    print("🔄 Conectando a la base de datos...")
    conexion = get_db()
    
    if conexion is None:
        print("❌ Error: No se pudo establecer conexión con la base de datos.")
        sys.exit(1)
    
    cursor = conexion.cursor()
    print("✅ Conexión establecida.")
    
    # 1. Agregar columna destacada a la tabla marcas
    print("\n🚀 Agregando columna 'destacada' a la tabla 'marcas'...")
    cursor.execute("""
        ALTER TABLE marcas 
        ADD COLUMN IF NOT EXISTS destacada BOOLEAN DEFAULT FALSE
    """)
    conexion.commit()
    print("✅ Columna 'destacada' agregada exitosamente.")
    
    # 2. Crear índice para optimizar consultas
    print("\n🔧 Creando índice para optimización...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_marcas_destacada ON marcas(destacada)")
    conexion.commit()
    print("✅ Índice creado exitosamente.")
    
    # 3. Verificar que la columna existe
    print("\n✔️  Verificando columna creada...")
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'marcas' 
        AND column_name = 'destacada'
    """)
    
    if cursor.fetchone():
        print("✅ Columna 'destacada' existe en la tabla 'marcas'")
    else:
        print("❌ Error: La columna 'destacada' no fue creada correctamente")
    
    cursor.close()
    conexion.close()
    
    print("\n" + "="*60)
    print("🎉 ¡Migración completada exitosamente!")
    print("="*60)
    print("\n✨ Ahora puedes usar la función de 'marcas destacadas' correctamente.")
    
except Exception as e:
    print(f"\n❌ Error durante la migración: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

