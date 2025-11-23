# limpiar_migraciones.py
import sqlite3
import os

# Ruta a tu base de datos
db_path = 'database/sayri.db'  # Ajusta según tu configuración

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ver la versión actual
        cursor.execute("SELECT * FROM alembic_version;")
        print("Versión actual:", cursor.fetchall())
        
        # Limpiar
        cursor.execute("DELETE FROM alembic_version;")
        conn.commit()
        
        print("✅ Tabla alembic_version limpiada exitosamente")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print(f"❌ No se encuentra la base de datos en: {db_path}")