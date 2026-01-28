import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY:
    logger.error("❌ SECRET_KEY no configurada en variables de entorno")
    raise ValueError("SECRET_KEY debe estar definida")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Utilidades de Contraseña ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash de contraseña"""
    return pwd_context.hash(password)

# --- Manejo de Tokens ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT con los datos proporcionados"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencias de Usuario ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Obtiene el usuario actual decodificando el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            logger.warning("❌ Token sin username")
            raise credentials_exception
        return {"username": username, "role": role}
    except JWTError as e:
        logger.warning(f"❌ Error al decodificar JWT: {str(e)}")
        raise credentials_exception

# --- Control de Permisos ---
def check_admin_role(user: dict = Depends(get_current_user)) -> dict:
    """Verifica que el usuario tenga rol de administrador"""
    if user["role"] != "admin":
        logger.warning(f"❌ Acceso denegado para usuario no-admin: {user['username']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida para este rol"
        )
    return user

def check_vendedor_role(current_user: dict = Depends(get_current_user)) -> dict:
    """Verifica que el usuario sea vendedor o admin"""
    if current_user["role"] not in ["vendedor", "admin"]:
        logger.warning(f"❌ Acceso denegado para usuario: {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes para realizar esta acción"
        )
    return current_user