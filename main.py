from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update 
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi_mail import FastMail, MessageSchema, MessageType

# Importamos as configurações centralizadas
from app.core.config import settings, mail_conf

# ==================================================================
# IMPORTANTE: Importamos os modelos aqui para que o SQLAlchemy
# os registre na memória assim que o servidor subir.
# ==================================================================
from app.models.company import Company
from app.models.client import Client
from app.models.manager import Manager
from app.models.client_token import ClientToken
from app.models.client_achievement import ClientAchievement
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.daily_report import DailyReport
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.webhook import WebhookLog
from app.models.invite import Invite

try:
    from app.api.deps import get_db
except ImportError:
    from app.db.session import get_db 

# ==================================================================
# CONFIGURAÇÕES DE SEGURANÇA
# ==================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
RESET_TOKEN_EXPIRE_MINUTES = 15

# ==================================================================
# MODELOS PYDANTIC
# ==================================================================
class PasswordRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

# ==================================================================
# FUNÇÕES UTILITÁRIAS
# ==================================================================
def create_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "type": "reset", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Token inválido")
        return payload.get("sub") 
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Database Manager API",
        version="1.0.0",
        description="Backend do sistema StamFlow"
    )

    # ==================================================================
    # CONFIGURAÇÃO DE CORS (ATUALIZADA)
    # ==================================================================
    origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500", 
        "http://localhost:5500", 
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5001",
        "http://localhost:5001",
        "http://127.0.0.1:3000", 
        "http://localhost:3000",
        
        # DOMÍNIOS DE PRODUÇÃO (HTTPS)
        "https://login.stamflow.com.br",
        "https://gestor.stamflow.com.br",
        "https://painel.stamflow.com.br",
        "https://painel-empregado.stamflow.com.br",
        "https://stamflow.com.br",
        "https://www.stamflow.com.br"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins, 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ==================================================================
    # ROTAS DE RECUPERAÇÃO DE SENHA
    # ==================================================================
    
    @app.post("/auth/forgot-password", status_code=200)
    async def forgot_password(request: PasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
        # 1. Verifica se o cliente existe
        query = select(Client).where(Client.email == request.email)
        result = await db.execute(query)
        client = result.scalars().first()
        
        if not client:
            return {"message": "Se o e-mail existir, as instruções foram enviadas."}

        # 2. Gera Token
        token = create_reset_token(client.email)

        # 3. Gera Link (CORRIGIDO PARA PRODUÇÃO)
        # O link aponta para a página de reset no frontend de login
        base_url = settings.BASE_URL 
        reset_link = f"{base_url}/resetPassword.html?token={token}"
        
        # 4. Envia Email
        html_body = f"""
        <div style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #34D399;">Recuperação de Senha - StamFlow</h2>
            <p>Olá,</p>
            <p>Recebemos uma solicitação para redefinir sua senha.</p>
            <p>Clique no botão abaixo para criar uma nova senha:</p>
            <a href="{reset_link}" style="background-color: #34D399; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">Redefinir Minha Senha</a>
            <p>Ou copie e cole este link no navegador:</p>
            <p>{reset_link}</p>
            <p style="font-size: 12px; color: #777;">Este link expira em 15 minutos.</p>
            <p>Se não foi você, ignore este e-mail.</p>
        </div>
        """

        message = MessageSchema(
            subject="Redefinir Senha - StamFlow",
            recipients=[client.email],
            body=html_body,
            subtype=MessageType.html
        )

        fm = FastMail(mail_conf)
        background_tasks.add_task(fm.send_message, message)

        return {"message": "Instruções enviadas para seu e-mail."}

    @app.post("/auth/reset-password", status_code=200)
    async def reset_password(request: PasswordReset, db: AsyncSession = Depends(get_db)):
        # 1. Valida Token
        email = verify_reset_token(request.token)

        # 2. Gera Hash da nova senha
        new_hash = get_password_hash(request.new_password)

        # 3. Atualiza no Banco
        stmt = (
            update(Client)
            .where(Client.email == email)
            .values(senha_hash=new_hash) 
        )
        
        # Executa e Commita
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount == 0:
             # Caso raro onde o token é válido mas o email foi deletado nesse meio tempo
             raise HTTPException(status_code=404, detail="Usuário não encontrado.")

        return {"message": "Senha redefinida com sucesso! Faça login novamente."}

    app.include_router(api_router)
    return app

app = create_app()
