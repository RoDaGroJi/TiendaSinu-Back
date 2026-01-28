from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth, database

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/register", response_model=dict)
def registrar_usuario(
    datos: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Crea un nuevo usuario (solo admin)"""
    # Verificar que el rol sea válido
    if datos.role not in ["vendedor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol debe ser 'vendedor' o 'admin'"
        )
    
    # Verificar que el usuario no exista
    usuario_existente = db.query(models.User).filter(models.User.username == datos.username).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe"
        )
    
    # Crear nuevo usuario
    nuevo_usuario = models.User(
        username=datos.username,
        password_hash=auth.get_password_hash(datos.password),
        role=datos.role,
        status=True
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {
        "id": nuevo_usuario.id,
        "username": nuevo_usuario.username,
        "role": nuevo_usuario.role.value,
        "message": "Usuario creado exitosamente"
    }

@router.get("/usuarios", response_model=List[dict])
def listar_usuarios(
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.check_admin_role)
):
    """Lista todos los usuarios del sistema (solo admin)"""
    usuarios = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.value,
            "is_active": u.status
        }
        for u in usuarios
    ]
