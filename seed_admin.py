from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User, UserRole
from app.auth import get_password_hash
import sys

def create_first_admin():
    db: Session = SessionLocal()
    
    # Datos del administrador - Puedes cambiarlos aquí
    username = "admin_central"
    password = "SuperPassword2026" # ¡Cámbiala después!

    # Verificar si ya existe
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"Error: El usuario '{username}' ya existe.")
        db.close()
        return

    try:
        new_admin = User(
            username=username,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            status=True
        )
        
        db.add(new_admin)
        db.commit()
        print("------------------------------------------")
        print("✅ Administrador creado con éxito")
        print(f"👤 Usuario: {username}")
        print(f"🔑 Password: {password}")
        print("------------------------------------------")
        print("RECUERDA: Borra este script o cambia la contraseña después del primer login.")
        
    except Exception as e:
        print(f"❌ Error al crear el admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_first_admin()