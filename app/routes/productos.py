from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth, database

router = APIRouter(prefix="/productos", tags=["Productos"])

# --- VISTA PÚBLICA: Clientes ---
@router.get("/", response_model=List[schemas.ProductPublic])
def listar_productos_publico(db: Session = Depends(database.get_db)):
    """Lista todos los productos activos para clientes"""
    return db.query(models.Product).filter(models.Product.status == True).all()

@router.get("/{product_id}", response_model=schemas.ProductPublic)
def obtener_producto_publico(product_id: int, db: Session = Depends(database.get_db)):
    """Obtiene un producto específico para clientes"""
    producto = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.status == True
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.get("/categoria/{cat_name}", response_model=List[schemas.ProductPublic])
def listar_por_categoria(cat_name: str, db: Session = Depends(database.get_db)):
    """Lista productos por categoría para clientes"""
    return db.query(models.Product).filter(
        models.Product.category == cat_name, 
        models.Product.status == True
    ).all()

# --- VISTA PRIVADA: Admin ---
@router.get("/admin/all", response_model=List[schemas.ProductAdmin])
def listar_productos_admin(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_vendedor_role)
):
    """Lista todos los productos (activos e inactivos) para administradores"""
    from sqlalchemy.orm import joinedload
    return db.query(models.Product).options(joinedload(models.Product.stock)).all()

@router.post("/", response_model=schemas.ProductAdmin, status_code=status.HTTP_201_CREATED)
def crear_producto(
    producto: schemas.ProductCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Crea un nuevo producto (solo administrador)"""
    # Validar que no exista un producto con el mismo nombre
    producto_existente = db.query(models.Product).filter(
        models.Product.name == producto.name
    ).first()
    if producto_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un producto con ese nombre"
        )
    
    # Crear el producto
    nuevo_producto = models.Product(**producto.model_dump())
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    
    # Crear registro de stock automáticamente
    nuevo_stock = models.Stock(product_id=nuevo_producto.id, current_quantity=0)
    db.add(nuevo_stock)
    db.commit()
    
    return nuevo_producto

@router.patch("/{prod_id}", response_model=schemas.ProductAdmin)
def editar_producto(
    prod_id: int,
    producto_update: schemas.ProductUpdate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Edita un producto existente (solo administrador)"""
    db_prod = db.query(models.Product).filter(models.Product.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    update_data = producto_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_prod, key, value)
    
    db.commit()
    db.refresh(db_prod)
    return db_prod

@router.delete("/{product_id}")
def desactivar_producto(
    product_id: int, 
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Desactiva un producto (soft delete)"""
    producto = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto.status = False
    db.commit()
    return {"message": "Producto desactivado exitosamente", "id": product_id}