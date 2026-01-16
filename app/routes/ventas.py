from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from .. import models, schemas, auth, database

router = APIRouter(prefix="/ventas", tags=["Ventas y Pedidos"])

# --- ACCIÓN DEL CLIENTE: Registrar Pedido ---
# Este endpoint se llama justo antes de abrir el enlace de WhatsApp en el frontend
@router.post("/pedido-nuevo", response_model=schemas.SaleResponse)
def crear_pedido_cliente(
    pedido: schemas.SaleCreate, 
    db: Session = Depends(database.get_db)
):
    # 1. Crear la cabecera de la venta (Tabla Sales)
    nuevo_pedido = models.Sale(
        client_name=pedido.client_name,
        client_phone=pedido.client_phone,
        client_address=pedido.client_address,
        total_estimated=pedido.total_estimated,
        observations=pedido.observations,
        status=True 
    )
    db.add(nuevo_pedido)
    
    # Necesitamos hacer flush para obtener el ID de la venta antes de guardar los items
    db.flush() 

    # 2. Guardar el detalle de los productos (Tabla SaleItems)
    for item in pedido.items:
        detalle_producto = models.SaleItem(
            sale_id=nuevo_pedido.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            price_at_time=item.price_at_time
        )
        db.add(detalle_producto)

    try:
        db.commit()
        db.refresh(nuevo_pedido)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar los productos del pedido")
        
    return nuevo_pedido

# --- ACCIÓN DEL VENDEDOR: Listar Pedidos Recibidos ---
@router.get("/listado", response_model=List[schemas.SaleResponse])
def listar_pedidos(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    # El vendedor ve los pedidos para saber qué preparar
    return db.query(models.Sale).order_by(models.Sale.created_at.desc()).all()

# --- ACCIÓN DEL VENDEDOR: Confirmar Despacho ---
# Al despachar, se resta automáticamente del inventario
@router.post("/despachar/{pedido_id}")
def despachar_pedido(
    pedido_id: int,
    productos_a_descontar: List[schemas.MovementCreate], # Lista de items y cantidades
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user),
    desde_modulo_venta: bool = Query(False, description="Indica si la venta viene del módulo de venta")
):
    # 1. Verificar el pedido
    pedido = db.query(models.Sale).filter(models.Sale.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # 2. Calcular nuevo total basado en los items actuales del pedido
    # Primero intentamos obtener los precios de los items del pedido
    nuevo_total = 0.0
    for item in productos_a_descontar:
        # Buscar el item en el pedido para obtener el precio original
        sale_item = db.query(models.SaleItem).filter(
            and_(models.SaleItem.sale_id == pedido_id, models.SaleItem.product_id == item.product_id)
        ).first()
        
        if sale_item:
            # Usar el precio del item del pedido (puede haber sido modificado)
            nuevo_total += sale_item.price_at_time * item.quantity
        else:
            # Si no existe el item, usar el precio actual del producto como fallback
            producto = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if producto:
                nuevo_total += producto.sale_price * item.quantity
    
    # 3. Descontar cada producto del inventario
    user_record = db.query(models.User).filter(models.User.username == current_user["username"]).first()
    
    for item in productos_a_descontar:
        db_stock = db.query(models.Stock).filter(models.Stock.product_id == item.product_id).first()
        
        if not db_stock or db_stock.current_quantity < item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"No hay suficiente stock para el producto ID {item.product_id}"
            )
        
        # Restar stock
        db_stock.current_quantity -= item.quantity
        
        # Registrar el movimiento de egreso
        movimiento = models.Movement(
            product_id=item.product_id,
            user_id=user_record.id,
            quantity=item.quantity,
            type=models.MovementType.EGRESO,
            observation=f"Despacho pedido #{pedido_id}"
        )
        db.add(movimiento)
        
        # Actualizar items del pedido con las cantidades reales despachadas
        sale_item = db.query(models.SaleItem).filter(
            and_(models.SaleItem.sale_id == pedido_id, models.SaleItem.product_id == item.product_id)
        ).first()
        if sale_item:
            sale_item.quantity = item.quantity
            # Actualizar precio si el producto cambió de precio
            producto = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if producto:
                sale_item.price_at_time = producto.sale_price

    # 4. Actualizar total del pedido
    pedido.total_estimated = nuevo_total

    # 5. Marcar como completado (tanto si viene del módulo de venta como si se confirma despacho manualmente)
    pedido.status = False  # Completado
    
    db.commit()
    
    return {"message": "Pedido despachado e inventario actualizado", "total_actualizado": nuevo_total}

@router.get("/historial", response_model=List[schemas.SaleResponse])
def obtener_historial_ventas(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user),
    fecha: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD. Si no se proporciona, devuelve todas las ventas")
):
    query = db.query(models.Sale)
    
    # Si se proporciona una fecha, filtrar por esa fecha
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            # Filtrar por el día completo (desde 00:00 hasta 23:59:59)
            inicio_dia = datetime.combine(fecha_obj, datetime.min.time())
            fin_dia = datetime.combine(fecha_obj, datetime.max.time())
            query = query.filter(
                and_(
                    models.Sale.created_at >= inicio_dia,
                    models.Sale.created_at <= fin_dia
                )
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    return query.order_by(models.Sale.created_at.desc()).all()

@router.get("/ventas-hoy", response_model=List[schemas.SaleResponse])
def obtener_ventas_hoy(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Obtiene solo las ventas del día actual"""
    hoy = date.today()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())
    
    return db.query(models.Sale).filter(
        and_(
            models.Sale.created_at >= inicio_dia,
            models.Sale.created_at <= fin_dia
        )
    ).order_by(models.Sale.created_at.desc()).all()

@router.get("/pedidos-pendientes", response_model=List[schemas.SaleResponse])
def obtener_pedidos_pendientes(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Obtiene solo los pedidos pendientes (status=True)"""
    return db.query(models.Sale).filter(models.Sale.status == True).order_by(models.Sale.created_at.desc()).all()

@router.put("/actualizar/{pedido_id}", response_model=schemas.SaleResponse)
def actualizar_pedido(
    pedido_id: int,
    pedido_actualizado: schemas.SaleCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Actualiza un pedido permitiendo modificar items, cantidades y precios"""
    pedido = db.query(models.Sale).filter(models.Sale.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Calcular el total basado en los items actualizados (más seguro que confiar en el frontend)
    total_calculado = sum(item.quantity * item.price_at_time for item in pedido_actualizado.items)
    
    # Actualizar datos básicos del pedido
    pedido.client_name = pedido_actualizado.client_name
    pedido.client_phone = pedido_actualizado.client_phone
    pedido.client_address = pedido_actualizado.client_address
    pedido.total_estimated = total_calculado  # Usar el total calculado en el backend
    pedido.observations = pedido_actualizado.observations
    
    # Eliminar items antiguos
    db.query(models.SaleItem).filter(models.SaleItem.sale_id == pedido_id).delete()
    
    # Agregar nuevos items
    for item in pedido_actualizado.items:
        nuevo_item = models.SaleItem(
            sale_id=pedido_id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            price_at_time=item.price_at_time
        )
        db.add(nuevo_item)
    
    try:
        db.commit()
        db.refresh(pedido)
        return pedido
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar el pedido: {str(e)}")