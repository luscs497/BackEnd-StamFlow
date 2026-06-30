from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Request
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

# CORREÇÃO C1 (rate limiting): limiter central + handler de erro 429
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter
from app.middleware.csrf import CSRFMiddleware  # CORREÇÃO C3

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

    # CORREÇÃO C1: registra o rate limiter no app.
    # - app.state.limiter é exigido pelo slowapi para resolver os decorators.
    # - O handler converte estouros em HTTP 429 (Too Many Requests).
    # - O SlowAPIMiddleware aplica os limites declarados por rota.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CSRFMiddleware)  # CORREÇÃO C3: valida X-CSRF-Token em mutações

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
        "https://user.stamflow.com.br",
        "https://painel-empregado.stamflow.com.br",
        # CORREÇÃO: domínio do painel demo (decisão de produto, 2026-06).
        # Sem isso, o navegador bloqueia toda chamada do demo.stamflow.com.br
        # para a API antes de qualquer lógica do backend ser executada.
        "https://demo.stamflow.com.br",
        "https://stamflow.com.br",
        "https://www.stamflow.com.br"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins, 
        allow_credentials=True,
        # CORREÇÃO I4: antes era allow_methods=["*"] e allow_headers=["*"].
        # Combinado com allow_credentials=True, isso é mais permissivo que o
        # necessário. Restringimos ao que a aplicação de fato usa.
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Admin-Token", "X-CSRF-Token"],
    )

    # ==================================================================
    # ROTAS DE RECUPERAÇÃO DE SENHA
    # ==================================================================
    
    @app.post("/auth/forgot-password", status_code=200)
    @limiter.limit("5/hour")
    async def forgot_password(request: Request, body: PasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
        # 1. Verifica se o cliente existe
        query = select(Client).where(Client.email == body.email)
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
        <div style="margin:0;padding:0;background-color:#0b1120;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0b1120;padding:32px 0;">
            <tr><td align="center">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#0f172a;border-radius:16px;overflow:hidden;border:1px solid #1e293b;">
                <tr><td style="height:6px;background-color:#a855f7;background-image:linear-gradient(90deg,#38bdf8,#a855f7,#ec4899,#f59e0b);font-size:0;line-height:0;">&nbsp;</td></tr>
                <tr><td style="padding:36px 36px 28px 36px;font-family:Arial,Helvetica,sans-serif;color:#e2e8f0;">
                  <img src="https://login.stamflow.com.br/icon.png" width="48" height="48" alt="StamFlow" style="border-radius:14px;display:block;margin-bottom:14px;" />
                  <div style="font-size:22px;font-weight:bold;color:#ffffff;margin-bottom:2px;">StamFlow</div>
                  <div style="font-size:14px;color:#94a3b8;margin-bottom:24px;">Recupera\u00e7\u00e3o de senha</div>
                  <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 16px 0;">Ol\u00e1,</p>
                  <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 24px 0;">Recebemos uma solicita\u00e7\u00e3o para redefinir a senha da sua conta. Clique no bot\u00e3o abaixo para criar uma nova senha:</p>
                  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">
                    <tr><td align="center" style="border-radius:10px;background-color:#7c3aed;background-image:linear-gradient(90deg,#6366f1,#a855f7,#ec4899);">
                      <a href="{reset_link}" style="display:inline-block;padding:14px 32px;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:10px;">Redefinir minha senha</a>
                    </td></tr>
                  </table>
                  <p style="font-size:13px;line-height:1.6;color:#94a3b8;margin:0 0 6px 0;">Ou copie e cole este link no navegador:</p>
                  <p style="font-size:13px;line-height:1.5;color:#38bdf8;word-break:break-all;margin:0 0 24px 0;">{reset_link}</p>
                  <div style="border-top:1px solid #1e293b;padding-top:16px;">
                    <p style="font-size:12px;color:#64748b;margin:0 0 4px 0;">Este link expira em 15 minutos.</p>
                    <p style="font-size:12px;color:#64748b;margin:0;">Se voc\u00ea n\u00e3o solicitou isso, ignore este e-mail.</p>
                  </div>
                </td></tr>
              </table>
              <div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#475569;margin-top:16px;">&copy; StamFlow</div>
            </td></tr>
          </table>
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
    @limiter.limit("10/hour")
    async def reset_password(request: Request, body: PasswordReset, db: AsyncSession = Depends(get_db)):
        # 1. Valida Token
        email = verify_reset_token(body.token)

        # 2. Gera Hash da nova senha
        new_hash = get_password_hash(body.new_password)

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
