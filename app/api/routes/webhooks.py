from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.services.webhook_service import WebhookService
from app.api.deps import get_mp_sdk
from app.core.limiter import limiter  # rate limit global
import mercadopago

router = APIRouter()

@router.post("/mercadopago")
@limiter.exempt  # ISENTA o webhook do rate limit global: o Mercado Pago pode
                 # enviar muitas notificações de um mesmo IP em rajada, e
                 # bloquear isso significaria perder confirmação de pagamento.
                 # A proteção do webhook é a validação HMAC, não o rate limit.
async def mercadopago_webhook(request: Request, db: AsyncSession = Depends(get_db), sdk: mercadopago.SDK = Depends(get_mp_sdk)) -> JSONResponse:
    return await WebhookService.webhook(request=request, db=db, sdk=sdk)
