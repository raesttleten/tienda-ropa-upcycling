from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
import models

# Configuración
SECRET_KEY = "tu-clave-secreta-super-segura-cambiala-en-produccion-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ==================== FUNCIONES DE HASH ====================
def hash_password(password: str) -> str:
    """Hashear contraseña con bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña hasheada"""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== FUNCIONES JWT ====================
def crear_token(data: dict) -> str:
    """Crear token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verificar_token(token: str) -> dict:
    """Verificar y decodificar token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ==================== VALIDACIONES ====================
def validar_password(password: str) -> tuple[bool, str]:
    """Validar fortaleza de contraseña"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if not any(c.isupper() for c in password):
        return False, "Debe contener al menos una mayúscula"
    if not any(c.islower() for c in password):
        return False, "Debe contener al menos una minúscula"
    if not any(c.isdigit() for c in password):
        return False, "Debe contener al menos un número"
    return True, "Contraseña válida"


# ==================== OBTENER USUARIO ACTUAL ====================
async def obtener_usuario_actual(
        db: Session,
        token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[models.Usuario]:
    """
    Obtener usuario actual desde el token en la cookie.
    Retorna None si no hay token o es inválido (para rutas públicas).
    """
    if not token:
        return None

    payload = verificar_token(token)
    if not payload:
        return None

    usuario_id = payload.get("sub")
    if not usuario_id:
        return None

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    return usuario


async def obtener_usuario_requerido(
        db: Session,
        token: Optional[str] = Cookie(None, alias="access_token")
) -> models.Usuario:
    """
    Obtener usuario actual OBLIGATORIO (lanza error si no está autenticado).
    Usar en rutas protegidas.
    """
    usuario = await obtener_usuario_actual(db, token)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Debes iniciar sesión."
        )
    return usuario


async def verificar_admin(
        db: Session,
        token: Optional[str] = Cookie(None, alias="access_token")
) -> models.Usuario:
    """
    Verificar que el usuario sea administrador.
    """
    usuario = await obtener_usuario_requerido(db, token)
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren permisos de administrador."
        )
    return usuario