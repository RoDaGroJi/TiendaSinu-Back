from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

# --- ENUMS PARA RESTRICCIÓN DE DATOS ---

class UserRole(enum.Enum):
    admin = "admin"
    vendedor = "vendedor"

class MovementType(enum.Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"

# --- TABLAS DEL SISTEMA ---

class UnitMeasure(Base):
    """Tipos de medidas (gramo, kg, libra, unidad, cartón, etc.)"""
    __tablename__ = "unit_measures"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # 'gramo', 'kilogramo', 'libra', 'unidad', 'cartón'
    abbreviation = Column(String, unique=True, nullable=False)  # 'g', 'kg', 'lb', 'u', 'ctn'
    
    # Auditoría
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    presentations = relationship("Presentation", back_populates="unit_measure")


class Presentation(Base):
    """Presentaciones de un producto (variantes con medida y precio diferentes)"""
    __tablename__ = "presentations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    unit_measure_id = Column(Integer, ForeignKey("unit_measures.id"), nullable=False)
    
    quantity = Column(Float, nullable=False)  # Ej: 30 (para 30 huevos)
    purchase_price = Column(Float, nullable=False)  # Precio de compra para esta presentación
    sale_price = Column(Float, nullable=False)  # Precio de venta para esta presentación
    description = Column(String)  # Ej: "Cubeta de 30 huevos", "Huevo individual"
    
    # Stock de esta presentación
    current_stock = Column(Integer, default=0)  # Cantidad disponible de esta presentación
    
    # Auditoría
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    product = relationship("Product", back_populates="presentations")
    unit_measure = relationship("UnitMeasure", back_populates="presentations")
    sale_items = relationship("SaleItem", back_populates="presentation")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.vendedor)
    
    # Auditoría y Estado
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación: Un usuario puede registrar muchos movimientos de stock
    movements = relationship("Movement", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, index=True)
    purchase_price = Column(Float, default=0.0)
    sale_price = Column(Float, default=0.0)
    
    # Auditoría y Estado
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    presentations = relationship("Presentation", back_populates="product", cascade="all, delete-orphan")
    movements = relationship("Movement", back_populates="product")
    stock = relationship("Stock", uselist=False, back_populates="product", cascade="all, delete-orphan")


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    current_quantity = Column(Float, default=0.0)
    
    # Auditoría y Estado
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", back_populates="stock")


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # Quién hizo el movimiento
    quantity = Column(Float, nullable=False)
    type = Column(Enum(MovementType), nullable=False)  # INGRESO o EGRESO
    observation = Column(String)

    # Auditoría y Estado
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", back_populates="movements")
    user = relationship("User", back_populates="movements")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    client_phone = Column(String, nullable=False)
    client_address = Column(String, nullable=False)
    total_estimated = Column(Float, nullable=False)
    observations = Column(String)
    status = Column(Boolean, default=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- AGREGAR ESTA LÍNEA ---
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id"))
    presentation_id = Column(Integer, ForeignKey("presentations.id"))
    
    product_name = Column(String, nullable=False)  # Copiamos el nombre por historial
    presentation_description = Column(String)  # Descripción de la presentación (ej: "Cubeta")
    quantity = Column(Float, nullable=False)  # Cantidad de presentaciones vendidas
    price_at_time = Column(Float, nullable=False)  # Precio al momento de la venta

    # Relaciones
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
    presentation = relationship("Presentation", back_populates="sale_items")