"""Script para crear registros de stock faltantes para productos existentes"""
from app.database import Base, engine, SessionLocal
from app.models import Product, Stock

# Crear tablas
Base.metadata.create_all(engine)

# Obtener sesión
db = SessionLocal()

# Obtener todos los productos
productos = db.query(Product).all()

# Para cada producto, verificar si tiene stock
for producto in productos:
    stock_existente = db.query(Stock).filter(Stock.product_id == producto.id).first()
    if not stock_existente:
        print(f"Creando stock para producto: {producto.name}")
        nuevo_stock = Stock(product_id=producto.id, current_quantity=0)
        db.add(nuevo_stock)

db.commit()
print(f"✅ Stock actualizado para {len(productos)} productos")
db.close()
