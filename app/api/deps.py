from typing import Annotated, Optional, Any

from fastapi import Depends, HTTPException, status, Header, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.core.config import settings 
from app.db.session import get_db
from app.models.client import Client
from app.models.manager import Manager
from app.models.company import Company
from app.models.subscription import SubscriptionStatus

from datetime import datetime, timezone

import mercadopago

# Mantemos apenas para documentação Swagger, mas a lógica real usará cookies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ======================================
# DEPENDÊNCIA DE SEGURANÇA: ADMIN TOKEN
# ======================================
async def verify_admin_token(
    x_admin_token: str = Header(..., description="Token secreto para operações administrativas")
):
    if x_admin_token != settings.ADMIN_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de administrador inválido ou ausente."
        )

# ======================================
# DEPENDÊNCIA BASE: USUÁRIO AUTENTICADO (VIA COOKIE)
# ======================================

async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    # Tenta pegar do cookie primeiro
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    # Fallback para o header Authorization (útil para testes de API)
    token_header: Optional[str] = Depends(oauth2_scheme)
):
    """
    Valida o JWT (Cookie ou Header) e retorna o usuário.
    """
    token = access_token_cookie or token_header

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado (Cookie ou Header ausente)",
        )

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    user_id = payload.get("sub")
    user_type = payload.get("user_type")

    if not user_id or not user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado",
        )

    # Lógica Assíncrona para buscar o usuário
    if user_type == "client":
        result = await db.execute(select(Client).where(Client.id == int(user_id)))
        user = result.scalar_one_or_none()
    elif user_type == "manager":
        result = await db.execute(select(Manager).where(Manager.id == int(user_id)))
        user = result.scalar_one_or_none()
    elif user_type == "company":
        result = await db.execute(
        select(Company)
        .options(selectinload(Company.subscription))
        .where(Company.id == int(user_id))
    )
        user = result.scalar_one_or_none()
    else:
        user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou tipo inválido",
        )

    return user

# ======================================
# DEPENDÊNCIAS DE PAPÉIS (ROLES)
# ======================================

async def get_current_client(
    user = Depends(get_current_user),
):
    if not isinstance(user, Client):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para clientes",
        )
    return user

async def get_current_manager(
    user = Depends(get_current_user),
):
    if not isinstance(user, Manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para gestores",
        )
    return user

async def get_current_company(
    user = Depends(get_current_user),
):
    if not isinstance(user, Company):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para empresas",
        )
    return user

# ======================================
# DEPENDÊNCIA DE ASSINATURA ATIVA
# ======================================

async def check_active_subscription(user: Any = Depends(get_current_user)):
    subscription = user.active_subscription
    if not subscription:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Essa conta não possui assinatura ativa."
        )
    
    now_utc = datetime.now(timezone.utc)
    is_expired = subscription.end_date and subscription.end_date < now_utc
    is_not_active = subscription.status != SubscriptionStatus.active.value 

    if is_expired or is_not_active:
        raise HTTPException(
            status_code=403,
            detail="Sua assinatura expirou ou está inativa. Realize o pagamento para continuar."
        ) 
    return subscription

# ======================================
# DEPENDÊNCIA DE RESGATAR SDK DO MP
# ======================================

def get_mp_sdk():
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise HTTPException(
            status_code=500,
            detail="Token do Mercado Pago não está configurado."
        )
    return mercadopago.SDK(token)