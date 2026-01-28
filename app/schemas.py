from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    vendedor = "vendedor"

class MovementType(str, Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"

class BaseAuditSchema(BaseModel):
    status: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- ESQUEMAS PARA MEDIDAS ---
class UnitMeasureCreate(BaseModel):
    name: str
    abbreviation: str

class UnitMeasureResponse(BaseModel):
    id: int
    name: str
    abbreviation: str
    
    model_config = ConfigDict(from_attributes=True)

# --- ESQUEMAS PARA PRESENTACIONES ---
class PresentationCreate(BaseModel):
    unit_measure_id: int
    quantity: float
    purchase_price: float
    sale_price: float
    description: Optional[str] = None
    current_stock: int = 0

class PresentationUpdate(BaseModel):
    unit_measure_id: Optional[int] = None
    quantity: Optional[float] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    description: Optional[str] = None
    current_stock: Optional[int] = None

class PresentationResponse(BaseModel):
    id: int
    product_id: int
    unit_measure_id: int
    quantity: float
    purchase_price: float
    sale_price: float
    description: Optional[str]
    current_stock: int
    unit_measure: Optional[UnitMeasureResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- ESQUEMAS PARA PRODUCTOS ---
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    purchase_price: Optional[float] = 0.0
    sale_price: Optional[float] = 0.0
    # Las presentaciones se crean por separado

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None

class StockShort(BaseModel):
    current_quantity: float
    
    model_config = ConfigDict(from_attributes=True)

# Lo que ve el CLIENTE (Público)
class ProductPublic(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    sale_price: float
    presentations: List[PresentationResponse] = []

    model_config = ConfigDict(from_attributes=True)

# Lo que ve el ADMIN (Privado)
class ProductAdmin(ProductPublic):
    status: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
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
    presentation_id: Optional[int] = None
    product_name: str
    presentation_description: Optional[str] = None
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

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "vendedor"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    status: bool
    
    model_config = ConfigDict(from_attributes=True)

