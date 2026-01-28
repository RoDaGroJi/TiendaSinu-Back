import os
import bcrypt
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# Configuración de logging
logger = logging.getLogger(__name__)
logging.getLogger("passlib").setLevel(logging.ERROR)

# --- PARCHE DE COMPATIBILIDAD PARA PYTHON 3.13 ---
# Passlib busca 'bcrypt.__about__', que no existe en versiones modernas de bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('about', (object,), {'__version__': bcrypt.__version__})

# Parche para la función 'clock' eliminada en Python 3.13
if not hasattr(time, 'clock'):
    time.clock = time.perf_counter
# ------------------------------------------------

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY:
    logger.error("❌ SECRET_KEY no configurada en variables de entorno")
    # En producción (Railway), esto detendrá el inicio si falta la variable
    raise ValueError("SECRET_KEY debe estar definida en las variables de entorno")

# Configuración de hashing (Bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Utilidades de Contraseña ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash gestionando el límite de bcrypt"""
    try:
        # Bcrypt tiene un límite de 72 caracteres; truncamos para evitar errores
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"❌ Error en verificación de password: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """Genera un hash de contraseña seguro"""
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
            logger.warning("❌ Token sin username (sub)")
            raise credentials_exception
            
        return {"username": username, "role": role}
    except JWTError as e:
        logger.warning(f"❌ Error al decodificar JWT: {str(e)}")
        raise credentials_exception

# --- Control de Permisos ---
def check_admin_role(user: dict = Depends(get_current_user)) -> dict:
    """Verifica que el usuario tenga rol de administrador"""
    # Manejamos si el rol viene como objeto Enum o String
    user_role = user["role"].value if hasattr(user["role"], "value") else user["role"]
    
    if user_role != "admin":
        logger.warning(f"❌ Acceso denegado para: {user['username']} (Rol: {user_role})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida para este rol"
        )
    return user

def check_vendedor_role(current_user: dict = Depends(get_current_user)) -> dict:
    """Verifica que el usuario sea vendedor o admin"""
    user_role = current_user["role"].value if hasattr(current_user["role"], "value") else current_user["role"]
    
    if user_role not in ["vendedor", "admin"]:
        logger.warning(f"❌ Acceso insuficiente para: {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes para realizar esta acción"
        )
    return current_user