from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from .. import models, schemas, auth, database

router = APIRouter(prefix="/productos", tags=["Productos"])

# --- VISTA PÚBLICA: Clientes ---
@router.get("/", response_model=List[schemas.ProductPublic])
def listar_productos_publico(db: Session = Depends(database.get_db)):
    # Solo productos activos (status=True)
    return db.query(models.Product).filter(models.Product.status == True).all()

@router.get("/categoria/{cat_name}", response_model=List[schemas.ProductPublic])
def listar_por_categoria(cat_name: str, db: Session = Depends(database.get_db)):
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
    # Agregamos .options(joinedload(models.Product.stock))
    return db.query(models.Product).options(joinedload(models.Product.stock)).all()

@router.post("/", response_model=schemas.ProductAdmin, status_code=status.HTTP_201_CREATED)
def crear_producto(
    producto: schemas.ProductCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    # 1. Crear el producto
    nuevo_producto = models.Product(**producto.model_dump())
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    
    # 2. Inicializar el Stock en 0 para este producto
    nuevo_stock = models.Stock(product_id=nuevo_producto.id, current_quantity=0)
    db.add(nuevo_stock)
    db.commit()
    
    return nuevo_producto

@router.patch("/{prod_id}", response_model=schemas.ProductAdmin)
def editar_producto(
    prod_id: int,
    producto_update: schemas.ProductCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    db_prod = db.query(models.Product).filter(models.Product.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    for key, value in producto_update.model_dump().items():
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
    producto = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto.status = False
    db.commit()
    return {"message": "Producto desactivado exitosamente"}