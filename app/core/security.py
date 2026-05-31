from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from jose import jwt, JWTError
from passlib.context import CryptContext

# Importamos as configurações que você já definiu no config.py
from app.core.config import settings

# ==============================
# CONFIGURAÇÕES DE SEGURANÇA
# ==============================

# O CryptContext cuida do hashing de senhas. 
# O esquema "bcrypt" é o padrão seguro para salvar senhas no banco.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==============================
# HASH DE SENHA
# ==============================

def hash_password(password: str) -> str:
    """Gera o hash seguro da senha usando bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha informada corresponde ao hash salvo."""
    return pwd_context.verify(password, password_hash)


# ==============================
# CRIAÇÃO DE TOKENS JWT
# ==============================

def _create_token(
    *,
    subject: str,
    user_type: Literal["client", "manager"],
    company_id: Optional[int],
    manager_id: Optional[int],
    expires_delta: timedelta,
) -> str:
    # IMPORTANTE: Use datetime.now(timezone.utc) pois utcnow() está depreciado em versões novas do Python
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": subject,            # ID do usuário (sempre string no JWT)
        "user_type": user_type,    # Sua lógica de 'client' ou 'manager'
        "company_id": company_id,
        "manager_id": manager_id,
        "exp": expire,             # Timestamp de expiração
        "iat": datetime.now(timezone.utc), # Timestamp de criação
    }

    # Buscamos SECRET_KEY e ALGORITHM direto do seu settings
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    *,
    user_id: int,
    user_type: Literal["client", "manager"],
    company_id: Optional[int],
    manager_id: Optional[int]
) -> str:
    """Cria um access token JWT (curta duração definido no .env)."""
    return _create_token(
        subject=str(user_id),
        user_type=user_type,
        company_id=company_id,
        manager_id=manager_id,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    *,
    user_id: int,
    user_type: Literal["client", "manager"],
    company_id: Optional[int],
    manager_id: Optional[int]
) -> str:
    """Cria um refresh token JWT (longa duração definido no .env)."""
    return _create_token(
        subject=str(user_id),
        user_type=user_type,
        company_id=company_id,
        manager_id=manager_id,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ==============================
# DECODIFICAÇÃO E VALIDAÇÃO
# ==============================

def decode_token(token: str) -> dict:
    """Decodifica e valida um token JWT."""
    try:
        # Novamente, validamos usando os dados do .env
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        # Em produção, você pode querer customizar essa exceção para o FastAPI tratar como 401
        raise ValueError("Token inválido ou expirado")