from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Presentation, Product, UnitMeasure
from app.schemas import PresentationCreate, PresentationUpdate, PresentationResponse, UnitMeasureCreate, UnitMeasureResponse
from app.auth import get_current_user, check_admin_role

router = APIRouter(prefix="/presentaciones", tags=["presentaciones"])

# --- GESTIÓN DE MEDIDAS ---

@router.get("/medidas", response_model=List[UnitMeasureResponse])
def get_unit_measures(db: Session = Depends(get_db)):
    """Obtener todas las medidas disponibles"""
    measures = db.query(UnitMeasure).filter(UnitMeasure.status == True).all()
    return measures

@router.post("/medidas", response_model=UnitMeasureResponse)
def create_unit_measure(
    measure: UnitMeasureCreate,
    db: Session = Depends(get_db),
    current_user = Depends(check_admin_role)
):
    """Crear una nueva medida (solo admin)"""
    # Verificar que sea admin - ya validado por check_admin_role
    
    # Verificar que no exista
    existing = db.query(UnitMeasure).filter(
        (UnitMeasure.name == measure.name) | (UnitMeasure.abbreviation == measure.abbreviation)
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La medida ya existe")
    
    new_measure = UnitMeasure(name=measure.name, abbreviation=measure.abbreviation)
    db.add(new_measure)
    db.commit()
    db.refresh(new_measure)
    return new_measure

# --- GESTIÓN DE PRESENTACIONES ---

@router.post("/productos/{product_id}/presentaciones", response_model=PresentationResponse)
def create_presentation(
    product_id: int,
    presentation: PresentationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(check_admin_role)
):
    """Crear una presentación para un producto"""
    # Ya validado por check_admin_role
    
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    
    # Verificar que la medida existe
    measure = db.query(UnitMeasure).filter(UnitMeasure.id == presentation.unit_measure_id).first()
    if not measure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medida no encontrada")
    
    new_presentation = Presentation(
        product_id=product_id,
        **presentation.dict()
    )
    db.add(new_presentation)
    db.commit()
    db.refresh(new_presentation)
    return new_presentation

@router.get("/productos/{product_id}/presentaciones", response_model=List[PresentationResponse])
def get_product_presentations(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todas las presentaciones de un producto"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    
    presentations = db.query(Presentation).filter(
        (Presentation.product_id == product_id) & (Presentation.status == True)
    ).all()
    return presentations

@router.get("/presentaciones/{presentation_id}", response_model=PresentationResponse)
def get_presentation(
    presentation_id: int,
    db: Session = Depends(get_db)
):
    """Obtener una presentación específica"""
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentación no encontrada")
    return presentation

@router.put("/presentaciones/{presentation_id}", response_model=PresentationResponse)
def update_presentation(
    presentation_id: int,
    presentation_update: PresentationUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(check_admin_role)
):
    """Actualizar una presentación"""
    # Ya validado por check_admin_role
    
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentación no encontrada")
    
    update_data = presentation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(presentation, field, value)
    
    db.commit()
    db.refresh(presentation)
    return presentation

@router.delete("/presentaciones/{presentation_id}")
def delete_presentation(
    presentation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(check_admin_role)
):
    """Eliminar una presentación (soft delete)"""
    # Ya validado por check_admin_role
    
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentación no encontrada")
    
    presentation.status = False
    db.commit()
    return {"message": "Presentación eliminada"}
