from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

# --- ENUMS PARA RESTRICCIÓN DE DATOS ---

class UserRole(enum.Enum):
    ADMIN = "admin"
    VENDEDOR = "vendedor"

class MovementType(enum.Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"

# --- TABLAS DEL SISTEMA ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VENDEDOR)
    
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
    unit_measure = Column(String)  # 'kg' o 'unidad'
    category = Column(String, index=True)
    purchase_price = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    
    # Auditoría y Estado
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    stock = relationship("Stock", back_populates="product", uselist=False)
    movements = relationship("Movement", back_populates="product")


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
    product_name = Column(String, nullable=False) # Copiamos el nombre por historial
    quantity = Column(Float, nullable=False)
    price_at_time = Column(Float, nullable=False) # Precio al momento de la venta

    # Relaciones
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")