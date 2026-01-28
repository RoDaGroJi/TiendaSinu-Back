"""
Script para crear las tablas nuevas de presentaciones y medidas.
Ejecutar antes de correr la app.
"""

from app.database import engine, Base
from app.models import UnitMeasure, Presentation
from sqlalchemy.orm import Session


def crear_tablas():
    """Crear todas las tablas nuevas"""
    print("📊 Creando tablas de presentaciones y medidas...")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False
    
    return True


def insertar_medidas_comunes():
    """Insertar medidas comunes"""
    
    db = Session(bind=engine)
    
    medidas = [
        {"name": "gramo", "abbreviation": "g"},
        {"name": "kilogramo", "abbreviation": "kg"},
        {"name": "libra", "abbreviation": "lb"},
        {"name": "unidad", "abbreviation": "u"},
        {"name": "cartón", "abbreviation": "ctn"},
        {"name": "cubeta", "abbreviation": "cub"},
        {"name": "caja", "abbreviation": "cja"},
    ]
    
    print("📏 Insertando medidas comunes...")
    
    try:
        for medida in medidas:
            # Verificar si ya existe
            existing = db.query(UnitMeasure).filter(UnitMeasure.name == medida["name"]).first()
            if not existing:
                new_measure = UnitMeasure(**medida)
                db.add(new_measure)
                print(f"  ✅ Medida '{medida['name']}' agregada")
        
        db.commit()
        print("✅ Medidas insertadas exitosamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error insertando medidas: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    crear_tablas()
    insertar_medidas_comunes()
    print("\n✨ Migración completada")
