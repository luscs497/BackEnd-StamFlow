from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.services.webhook_service import WebhookService
from app.api.deps import get_mp_sdk
import mercadopago

router = APIRouter()

@router.post("/mercadopago")
async def mercadopago_webhook(request: Request, db: AsyncSession = Depends(get_db), sdk: mercadopago.SDK = Depends(get_mp_sdk)) -> JSONResponse:
    return await WebhookService.webhook(request=request, db=db, sdk=sdk)