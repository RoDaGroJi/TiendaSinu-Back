from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date, timedelta
from .. import models, schemas, auth, database

router = APIRouter(prefix="/ventas", tags=["Ventas y Pedidos"])

# --- CREAR PEDIDO (Cliente o Vendedor) ---
@router.post("/pedido-nuevo", response_model=schemas.SaleResponse)
def crear_pedido_cliente(
    pedido: schemas.SaleCreate, 
    db: Session = Depends(database.get_db)
):
    """Crea un nuevo pedido con items asociados"""
    # Validar datos básicos
    if not pedido.client_name or not pedido.client_phone:
        raise HTTPException(
            status_code=400,
            detail="Nombre y teléfono del cliente son requeridos"
        )
    
    if len(pedido.items) == 0:
        raise HTTPException(
            status_code=400,
            detail="El pedido debe contener al menos un producto"
        )
    
    # Crear la cabecera de la venta
    nuevo_pedido = models.Sale(
        client_name=pedido.client_name,
        client_phone=pedido.client_phone,
        client_address=pedido.client_address,
        total_estimated=pedido.total_estimated,
        observations=pedido.observations,
        status=True 
    )
    db.add(nuevo_pedido)
    db.flush() 

    # Guardar los detalles de los productos
    for item in pedido.items:
        detalle_producto = models.SaleItem(
            sale_id=nuevo_pedido.id,
            product_id=item.product_id,
            presentation_id=item.presentation_id,
            product_name=item.product_name,
            presentation_description=item.presentation_description,
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

# --- LISTAR PEDIDOS ---
@router.get("/listado", response_model=List[schemas.SaleResponse])
def listar_pedidos(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Lista todos los pedidos ordenados por fecha"""
    return db.query(models.Sale).order_by(models.Sale.created_at.desc()).all()

@router.get("/pedidos-pendientes", response_model=List[schemas.SaleResponse])
def obtener_pedidos_pendientes(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    """Obtiene solo los pedidos pendientes (status=True)"""
    return db.query(models.Sale).filter(models.Sale.status == True).order_by(
        models.Sale.created_at.desc()
    ).all()

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

@router.get("/historial", response_model=List[schemas.SaleResponse])
def obtener_historial_ventas(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user),
    fecha: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD")
):
    """Obtiene historial de ventas, opcionalmente filtrado por fecha"""
    query = db.query(models.Sale)
    
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
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

# --- ACTUALIZAR PEDIDO ---
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
    
    # Calcular el total basado en los items actualizados
    total_calculado = sum(item.quantity * item.price_at_time for item in pedido_actualizado.items)
    
    # Actualizar datos básicos del pedido
    pedido.client_name = pedido_actualizado.client_name
    pedido.client_phone = pedido_actualizado.client_phone
    pedido.client_address = pedido_actualizado.client_address
    pedido.total_estimated = total_calculado
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
        raise HTTPException(status_code=500, detail="Error al actualizar el pedido")

# --- DESPACHAR PEDIDO ---
@router.post("/despachar/{pedido_id}")
def despachar_pedido(
    pedido_id: int,
    productos_a_descontar: List[schemas.MovementCreate],
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user),
    desde_modulo_venta: bool = Query(False)
):
    """Despacha un pedido y actualiza el inventario"""
    # Verificar el pedido
    pedido = db.query(models.Sale).filter(models.Sale.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Calcular nuevo total
    nuevo_total = 0.0
    for item in productos_a_descontar:
        sale_item = db.query(models.SaleItem).filter(
            and_(models.SaleItem.sale_id == pedido_id, models.SaleItem.product_id == item.product_id)
        ).first()
        
        if sale_item:
            nuevo_total += sale_item.price_at_time * item.quantity
        else:
            producto = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if producto:
                nuevo_total += producto.sale_price * item.quantity
    
    # Obtener usuario actual
    user_record = db.query(models.User).filter(models.User.username == current_user["username"]).first()
    
    # Descontar cada producto del inventario
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
            type=models.MovementType.EGRESO.value.upper(),
            observation=f"Despacho pedido #{pedido_id}"
        )
        db.add(movimiento)
        
        # Actualizar items del pedido
        sale_item = db.query(models.SaleItem).filter(
            and_(models.SaleItem.sale_id == pedido_id, models.SaleItem.product_id == item.product_id)
        ).first()
        if sale_item:
            sale_item.quantity = item.quantity

    # Actualizar total del pedido
    pedido.total_estimated = nuevo_total
    pedido.status = False
    
    db.commit()
    
    return {"message": "Pedido despachado e inventario actualizado", "total_actualizado": nuevo_total}

# --- ESTADÍSTICAS ---
@router.get("/estadisticas/resumen")
def obtener_estadisticas_resumen(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role),
    periodo: str = Query("hoy", description="hoy, semana, mes, todo"),
    fecha_inicio: Optional[str] = Query(None, description="YYYY-MM-DD"),
    fecha_fin: Optional[str] = Query(None, description="YYYY-MM-DD")
):
    """Obtiene estadísticas de ventas filtradas por período (solo admin)"""
    query = db.query(
        func.count(models.Sale.id).label("total_pedidos"),
        func.sum(models.Sale.total_estimated).label("total_vendido"),
        func.avg(models.Sale.total_estimated).label("promedio_pedido")
    )
    
    if periodo == "hoy":
        hoy = date.today()
        inicio = datetime.combine(hoy, datetime.min.time())
        fin = datetime.combine(hoy, datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif periodo == "semana":
        hoy = date.today()
        inicio = datetime.combine(hoy - timedelta(days=hoy.weekday()), datetime.min.time())
        fin = datetime.combine(hoy, datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif periodo == "mes":
        hoy = date.today()
        inicio = datetime.combine(date(hoy.year, hoy.month, 1), datetime.min.time())
        if hoy.month == 12:
            fin = datetime.combine(date(hoy.year + 1, 1, 1) - timedelta(days=1), datetime.max.time())
        else:
            fin = datetime.combine(date(hoy.year, hoy.month + 1, 1) - timedelta(days=1), datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif fecha_inicio and fecha_fin:
        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido")
    
    resultado = query.first()
    
    return {
        "total_pedidos": resultado[0] or 0,
        "total_vendido": resultado[1] or 0,
        "promedio_pedido": round(resultado[2] or 0, 2),
        "periodo": periodo
    }

@router.get("/estadisticas/por-producto")
def obtener_estadisticas_por_producto(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role),
    periodo: str = Query("mes", description="hoy, semana, mes, todo"),
    fecha_inicio: Optional[str] = Query(None, description="YYYY-MM-DD"),
    fecha_fin: Optional[str] = Query(None, description="YYYY-MM-DD")
):
    """Obtiene estadísticas de ventas por producto (solo admin)"""
    query = db.query(
        models.SaleItem.product_name,
        func.count(models.SaleItem.id).label("cantidad_vendida"),
        func.sum(models.SaleItem.quantity).label("unidades_totales"),
        func.sum(models.SaleItem.quantity * models.SaleItem.price_at_time).label("ingresos")
    ).group_by(models.SaleItem.product_name)
    
    # Filtrar por período
    if periodo == "hoy":
        hoy = date.today()
        inicio = datetime.combine(hoy, datetime.min.time())
        fin = datetime.combine(hoy, datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif periodo == "semana":
        hoy = date.today()
        inicio = datetime.combine(hoy - timedelta(days=hoy.weekday()), datetime.min.time())
        fin = datetime.combine(hoy, datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif periodo == "mes":
        hoy = date.today()
        inicio = datetime.combine(date(hoy.year, hoy.month, 1), datetime.min.time())
        if hoy.month == 12:
            fin = datetime.combine(date(hoy.year + 1, 1, 1) - timedelta(days=1), datetime.max.time())
        else:
            fin = datetime.combine(date(hoy.year, hoy.month + 1, 1) - timedelta(days=1), datetime.max.time())
        query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
    elif fecha_inicio and fecha_fin:
        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(and_(models.Sale.created_at >= inicio, models.Sale.created_at <= fin))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido")
    
    query = query.join(models.Sale).order_by(func.sum(models.SaleItem.quantity * models.SaleItem.price_at_time).desc())
    
    resultados = query.all()
    
    return [
        {
            "producto": r[0],
            "cantidad_transacciones": r[1],
            "unidades_totales": r[2],
            "ingresos": round(r[3] or 0, 2)
        }
        for r in resultados
    ]

@router.get("/estadisticas/vendedor-hoy")
def obtener_venta_vendedor_hoy(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_vendedor_role)
):
    """Obtiene el resumen de ventas del vendedor hoy"""
    hoy = date.today()
    inicio = datetime.combine(hoy, datetime.min.time())
    fin = datetime.combine(hoy, datetime.max.time())
    
    ventas = db.query(models.Sale).filter(
        and_(
            models.Sale.created_at >= inicio,
            models.Sale.created_at <= fin
        )
    ).all()
    
    total_vendido = sum(v.total_estimated for v in ventas)
    
    return {
        "usuario": current_user["username"],
        "fecha": str(hoy),
        "total_pedidos": len(ventas),
        "total_vendido": total_vendido,
        "promedio_pedido": round(total_vendido / len(ventas), 2) if ventas else 0,
        "detalle_ventas": ventas
    }
