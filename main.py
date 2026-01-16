from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import auth, models, database
from app.database import engine, Base
from app import models
from fastapi.middleware.cors import CORSMiddleware # Importar el middleware
# Importamos las rutas
from app.routes import productos, inventario, ventas

app = FastAPI()

origins = [
    "http://localhost:5173",    # Puerto por defecto de Vite
    "http://127.0.0.1:5173",
    "http://TU_IP_LOCAL:5173",  # Pon la IP de tu PC si pruebas desde otro dispositivo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Permite estas URLs
    allow_credentials=True,
    allow_methods=["*"],               # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],               # Permite todos los encabezados (tokens, etc.)
)
models.Base.metadata.create_all(bind=engine)

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    # Buscamos al usuario en la base de datos
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Creamos el token incluyendo el ROL
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role.value}

app.include_router(productos.router)
app.include_router(inventario.router)
app.include_router(ventas.router)
