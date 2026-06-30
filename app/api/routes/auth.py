from typing import Any, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Body, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    ClientCreate, 
    LoginResponse, 
    TokenResponse, 
    AuthUser, 
    ClientResponse,
    ClientBulkDelete
)

from app.api.deps import get_current_user, verify_admin_token 
from app.models.client import Client
from app.models.manager import Manager
from app.models.company import Company
from app.core.config import settings
from app.core.limiter import limiter
from app.middleware.csrf import generate_csrf_token  # CORREÇÃO C3

router = APIRouter()

class UserUpdate(BaseModel):
    nome_completo: Optional[str] = None
    email: Optional[str] = None 

# ======================================================================
# 1. REGISTER (PROTEGIDO)
# ======================================================================
@router.post(
    "/register", 
    response_model=ClientResponse, 
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/hour")
async def register_client(
    request: Request,
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    new_client = await AuthService.register_client(db, client_data)
    return new_client

# ======================================================================
# 2. LOGIN (COOKIES GLOBAIS .STAMFLOW.COM.BR)
# ======================================================================
@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    response: Response, # Injeção do objeto Response para setar cookies
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Autenticação
    user, user_type = await AuthService.authenticate_user(
        db, 
        email=form_data.username, 
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail/Login ou senha incorretos",
        )

    company_id = getattr(user, "company_id", None)
    manager_id = getattr(user, "manager_id", None)
    
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else "0.0.0.0"
    
    # Gera tokens
    access_token, refresh_token = await AuthService.create_tokens_for_user(
        db, 
        user_id=user.id, 
        user_type=user_type, 
        company_id=company_id,
        manager_id=manager_id,
        user_agent=user_agent,
        ip=client_ip
    )

    # --- DEFINE COOKIES SEGUROS E GLOBAIS ---
    # Access Token (Curta duração)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,   # JavaScript não lê (Segurança contra XSS)
        secure=True,     # OBRIGATÓRIO EM HTTPS
        samesite="lax",  # Permite navegação entre subdomínios
        domain=".stamflow.com.br", # O PULO DO GATO: Compartilha entre login, api e painel
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    # Refresh Token (Longa duração)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,     # OBRIGATÓRIO EM HTTPS
        samesite="lax",
        domain=".stamflow.com.br", 
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    # CSRF Token (CORREÇÃO C3) — NÃO httponly: o JS dos painéis precisa lê-lo
    # para injetar no header X-CSRF-Token em toda chamada de mutação.
    # Gerado a cada login; renovado a cada refresh.
    response.set_cookie(
        key="csrf_token",
        value=generate_csrf_token(),
        httponly=False,   # intencional: JS precisa ler
        secure=True,
        samesite="lax",
        domain=".stamflow.com.br",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    # Resposta JSON (Sem tokens, apenas dados do usuário)
    user_email_display = user.email

    return LoginResponse(
        user=AuthUser(
            id=user.id,
            email=user_email_display,
            user_type=user_type,
            company_id=company_id,
            manager_id=manager_id
        ),
        access_token=access_token,
        token_type="bearer",
        message="Login realizado com sucesso"
    )

# ======================================================================
# 3. REFRESH TOKEN (VIA COOKIE GLOBAL)
# ======================================================================
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"), # Pega do cookie
    db: AsyncSession = Depends(get_db)
):
    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="Refresh token ausente")

    # Renova
    new_access, current_refresh = await AuthService.refresh_access_token(
        db, 
        refresh_token=refresh_token_cookie
    )

    # Atualiza o cookie de Access Token
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".stamflow.com.br",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    # CORREÇÃO C3: renova o csrf_token a cada refresh para rotação contínua
    response.set_cookie(
        key="csrf_token",
        value=generate_csrf_token(),
        httponly=False,
        secure=True,
        samesite="lax",
        domain=".stamflow.com.br",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return TokenResponse(message="Token renovado")

# ======================================================================
# 3.5 LOGOUT (LIMPA COOKIES GLOBAIS)
# ======================================================================
@router.post("/logout")
async def logout(response: Response):
    # Para apagar o cookie, precisamos passar os mesmos parâmetros de criação
    response.delete_cookie("access_token", domain=".stamflow.com.br", secure=True, httponly=True)
    response.delete_cookie("refresh_token", domain=".stamflow.com.br", secure=True, httponly=True)
    # CORREÇÃO C3: apaga o csrf_token junto com os demais cookies de sessão
    response.delete_cookie("csrf_token", domain=".stamflow.com.br", secure=True)
    return {"message": "Logout realizado com sucesso"}

# ==============================================================================
# 4. ROTA DE PERFIL (GET /me)
# ==============================================================================
@router.get("/me")
async def read_users_me(
    current_user: Any = Depends(get_current_user)
):
    if isinstance(current_user, Client):
        return {
            "id": current_user.id,
            "nome_completo": current_user.nome_completo,
            "email": current_user.email,
            "tipo": "client",
            "company_id": current_user.company_id,
            "manager_id": current_user.manager_id
        }
    
    elif isinstance(current_user, Manager):
        return {
            "id": current_user.id,
            "nome_completo": current_user.nome, 
            "email": current_user.email,        
            "tipo": "manager",
            "company_id": current_user.company_id
        }
    
    elif isinstance(current_user, Company):
        return {
            "id": current_user.id,
            "nome_completo": current_user.nome_fantasia, 
            "email": current_user.email,        
            "tipo": "company"
        }
    
    raise HTTPException(status_code=400, detail="Tipo de usuário desconhecido")

# ==============================================================================
# 5. ROTA DE ATUALIZAR PERFIL (PUT /me)
# ==============================================================================
@router.put("/me")
async def update_user_me(
    user_update: UserUpdate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # --- CLIENTE ---
    if isinstance(current_user, Client):
        if user_update.nome_completo:
            current_user.nome_completo = user_update.nome_completo
        
        if user_update.email and user_update.email != current_user.email:
            q = select(Client).where(Client.email == user_update.email, Client.id != current_user.id)
            res = await db.execute(q)
            if res.scalar():
                raise HTTPException(status_code=400, detail="Email já está em uso.")
            current_user.email = user_update.email
            
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
        return {"nome_completo": current_user.nome_completo if current_user.nome_completo else "Colaborador(a)", "email": current_user.email}

    # --- GESTOR ---
    elif isinstance(current_user, Manager):
        if user_update.nome_completo:
            current_user.nome = user_update.nome_completo
        
        if user_update.email and user_update.email != current_user.email:
            q = select(Manager).where(Manager.email == user_update.email, Manager.id != current_user.id)
            res = await db.execute(q)
            if res.scalar():
                raise HTTPException(status_code=400, detail="Email já está em uso.")
            current_user.email = user_update.email
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
            
        return {"nome_completo": current_user.nome, "email": current_user.email}
    
    # --- EMPRESA ---
    elif isinstance(current_user, Company):
        if user_update.nome_completo:
            current_user.nome_fantasia = user_update.nome_completo
        
        if user_update.email and user_update.email != current_user.email:
            q = select(Company).where(Company.email == user_update.email, Company.id != current_user.id)
            res = await db.execute(q)
            if res.scalar():
                raise HTTPException(status_code=400, detail="Email já está em uso.")
            current_user.email = user_update.email
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
            
        return {"nome": current_user.nome_fantasia, "email": current_user.email}

    raise HTTPException(status_code=400, detail="Não foi possível atualizar.")

# ==============================================================================
# 6. ESQUECI MINHA SENHA
# ==============================================================================
# REMOVIDO (correção I3): esta rota era uma SEGUNDA implementação de
# /auth/forgot-password que apenas dava print() do e-mail e do ID do usuário
# no stdout/journal (vazamento de PII nos logs) e NÃO enviava e-mail algum.
# A implementação real e funcional — que de fato gera o token e dispara o
# e-mail via FastMail, agora com rate limiting — está em main.py.
# Manter as duas era um risco: dependendo da ordem de registro, a rota inócua
# poderia "vencer" a funcional. Removida para deixar uma única fonte da verdade.

# ==============================================================================
# 6. DELETAR CLIENTS EM MASSA
# ==============================================================================
@router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clients_bulk(
    db: Annotated[AsyncSession, Depends(get_db)], 
    data: ClientBulkDelete,
    current_user: Annotated[Any, Depends(get_current_user)]
):
    await AuthService.delete_clients_bulk(db, current_user, data.client_ids)

# ==============================================================================
# 7. DELETAR CLIENT
# ==============================================================================
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[Any, Depends(get_current_user)], client_id: int):
    await AuthService.delete_client(db, current_user, client_id)
