import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from app import auth, models, database
from app.database import engine, Base
from app.routes import productos, inventario, ventas, presentaciones, auth_users

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SinuTienda API",
    description="API para gestión de tienda con inventario y ventas",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://TU_IP_LOCAL:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)
logger.info("✅ Base de datos inicializada")

@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verificar estado de la API"""
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/", tags=["Sistema"])
async def root():
    """Información de la API"""
    return {"nombre": "SinuTienda API", "version": "1.0.0", "docs": "/docs"}

@app.post("/token", tags=["Autenticación"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    """Endpoint para autenticar usuario y obtener token JWT"""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        logger.warning(f"❌ Intento de login fallido para usuario: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.status:
        logger.warning(f"❌ Intento de login con usuario inactivo: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    logger.info(f"✅ Login exitoso para usuario: {form_data.username}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username
    }

app.include_router(productos.router)
app.include_router(inventario.router)
app.include_router(ventas.router)
app.include_router(presentaciones.router)
app.include_router(auth_users.router)
