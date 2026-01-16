from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VENDEDOR = "vendedor"

class MovementType(str, Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"

class BaseAuditSchema(BaseModel):
    status: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Lo que se necesita para crear un producto
class ProductCreate(BaseModel):
    name: str
    description: str
    unit_measure: str # 'kg' o 'unidad'
    purchase_price: float
    sale_price: float
    category: str

class StockShort(BaseModel):
    current_quantity: float
    
    model_config = ConfigDict(from_attributes=True)

# Lo que ve el CLIENTE (Público)
class ProductPublic(BaseModel):
    id: int
    name: str
    description: str
    unit_measure: str
    sale_price: float
    category: str

# Lo que ve el ADMIN (Privado)
class ProductAdmin(ProductPublic):
    purchase_price: float
    status: bool
    # Agregamos la relación aquí para que Pydantic la procese
    stock: Optional[StockShort] = None 
    
    model_config = ConfigDict(from_attributes=True)
    

class StockSchema(BaseModel):
    product_id: int
    current_quantity: float
    
    model_config = ConfigDict(from_attributes=True)

class MovementCreate(BaseModel):
    product_id: int
    quantity: float
    type: MovementType
    observation: Optional[str] = None
    # El user_id se obtendrá automáticamente del token JWT en el backend

class MovementResponse(BaseAuditSchema):
    id: int
    product_id: int
    user_id: int
    quantity: float
    type: MovementType
    observation: Optional[str] = None

# Esquema para los productos individuales dentro de una venta
class SaleItemSchema(BaseModel):
    product_id: int
    product_name: str
    quantity: float
    price_at_time: float

    model_config = ConfigDict(from_attributes=True)
    
class SaleCreate(BaseModel):
    client_name: str
    client_phone: str
    client_address: str
    total_estimated: float
    observations: Optional[str] = None
    # --- AHORA RECIBE LA LISTA DE PRODUCTOS ---
    items: List[SaleItemSchema] 

class SaleResponse(BaseAuditSchema):
    id: int
    client_name: str
    client_phone: str
    client_address: str
    total_estimated: float
    observations: Optional[str] = None
    # --- AHORA DEVUELVE LA LISTA DE PRODUCTOS AL FRONTEND ---
    items: List[SaleItemSchema] = []

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole

class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    status: bool

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

