from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth, database

router = APIRouter(prefix="/inventario", tags=["Inventario"])

# --- VISTA DE STOCK ACTUAL (Vendedor y Admin) ---
@router.get("/stock", response_model=List[schemas.StockSchema])
def ver_stock_actual(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Obtiene el stock actual de todos los productos"""
    return db.query(models.Stock).all()

@router.get("/stock/{product_id}", response_model=schemas.StockSchema)
def obtener_stock_producto(
    product_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Obtiene el stock de un producto específico"""
    stock = db.query(models.Stock).filter(models.Stock.product_id == product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock no encontrado para este producto")
    return stock

# --- REGISTRAR MOVIMIENTO (Ingreso o Egreso) ---
@router.post("/movimiento", response_model=schemas.MovementResponse)
def registrar_movimiento(
    movimiento: schemas.MovementCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Registra un movimiento de ingreso o egreso de inventario"""
    # 1. Verificar si el producto existe
    db_stock = db.query(models.Stock).filter(models.Stock.product_id == movimiento.product_id).first()
    if not db_stock:
        raise HTTPException(status_code=404, detail="El producto no tiene registro de stock")

    # 2. Validar permisos: Solo ADMIN puede hacer INGRESOS
    if movimiento.type == schemas.MovementType.INGRESO and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Solo el administrador puede registrar ingresos de mercancía"
        )

    # 3. Validar stock suficiente si es un EGRESO
    if movimiento.type == schemas.MovementType.EGRESO:
        if db_stock.current_quantity < movimiento.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Stock insuficiente. Disponible: {db_stock.current_quantity}"
            )
        db_stock.current_quantity -= movimiento.quantity
    else:
        # Es un INGRESO
        db_stock.current_quantity += movimiento.quantity

    # 4. Obtener el ID del usuario que está operando
    user_record = db.query(models.User).filter(models.User.username == current_user["username"]).first()

    # 5. Crear el registro del movimiento para auditoría
    nuevo_movimiento = models.Movement(
        product_id=movimiento.product_id,
        user_id=user_record.id,
        quantity=movimiento.quantity,
        type=movimiento.type.value.upper(),  # Guardar como INGRESO o EGRESO
        observation=movimiento.observation,
        status=True
    )
    
    db.add(nuevo_movimiento)
    db.commit()
    db.refresh(db_stock)
    db.refresh(nuevo_movimiento)
    
    return nuevo_movimiento

# --- HISTORIAL DE MOVIMIENTOS (Solo Admin) ---
@router.get("/historial", response_model=List[schemas.MovementResponse])
def ver_historial_completo(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Obtiene el historial completo de movimientos de inventario"""
    return db.query(models.Movement).order_by(models.Movement.created_at.desc()).all()

@router.get("/historial/producto/{product_id}", response_model=List[schemas.MovementResponse])
def ver_historial_producto(
    product_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Obtiene el historial de movimientos de un producto específico"""
    return db.query(models.Movement).filter(
        models.Movement.product_id == product_id
    ).order_by(models.Movement.created_at.desc()).all()