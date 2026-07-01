from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from app.db.session import get_db
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.subscription_plan import PlanPeriod
from app.models.webhook import WebhookLog, WebhookStatus
from app.api.deps import get_mp_sdk
from app.core.config import settings
import mercadopago
import logging
import json

import hmac
import hashlib
import time
from fastapi.responses import JSONResponse
from app.services.utils import mp_call

router = APIRouter()

logger = logging.getLogger("webhook")
logging.basicConfig(level=logging.INFO)


PERIOD_DELTA = {
                    PlanPeriod.monthly.value: relativedelta(months=1),
                    PlanPeriod.quarterly.value: relativedelta(months=3),
                    PlanPeriod.semiannual.value: relativedelta(months=6),
                    PlanPeriod.annual.value: relativedelta(years=1),
                }
class WebhookService:
    @staticmethod
    def verify_mp_signature(
        x_signature: str,
        x_request_id: str,
        resource_id: str,
        secret: str,
        max_time_seconds: int = 300
    ) -> bool:
        """
        Retorna True se a assinatura HMAC-SHA256 do webhook for válida.
        Retorna False em qualquer caso de falha (header ausente, formato inválido,
        assinatura incorreta).
        """
        if (not x_signature or not x_request_id or not secret or not resource_id):
            return False
    
        # Parseia "ts=...;v1=..."
        parts: dict[str, str] = {}
        for segment in x_signature.split(";"):
            if "=" in segment:
                k, v = segment.split("=", 1)
                parts[k.strip()] = v.strip()
    
        ts = parts.get("ts", "")
        received_hash = parts.get("v1", "")
    
        if not ts or not received_hash:
            return False
        
        try:
            ts_age = abs(int(time.time()) - int(ts))
            if ts_age > max_time_seconds:
                return False
        except (ValueError, TypeError):
            return False
    
        manifest = f"id:{resource_id};request-id:{x_request_id};ts:{ts};"
        expected_hash = hmac.new(
            secret.encode("utf-8"),
            manifest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    
        # compare_digest previne timing attacks
        return hmac.compare_digest(expected_hash, received_hash)
    
    @staticmethod
    async def already_processed(db: AsyncSession, topic: str | None, resource_id: str | None) -> bool:
        # Idempotência: o MP reenvia o MESMO webhook várias vezes de propósito
        # (garantia de entrega). Consideramos "já processado" se existe registro
        # em qualquer status TERMINAL (success, ignored ou error) para o mesmo
        # (topic, resource_id). Não barramos por 'processing', pois esse é um
        # estado transitório — se um webhook travou em processing por um crash,
        # queremos que um reenvio possa retomá-lo.
        # Antes: só considerava 'success', o que deixava reenvios de webhooks
        # terminados como 'ignored' colidirem na constraint única
        # (topic, resource_id, status) e estourarem 500 no commit.
        if not topic or not resource_id:
            return False

        stmt = (
            select(WebhookLog.id)
            .where(WebhookLog.topic == topic)
            .where(WebhookLog.resource_id == str(resource_id))
            .where(WebhookLog.status.in_([
                WebhookStatus.success,
                WebhookStatus.ignored,
                WebhookStatus.error,
            ]))
            .limit(1)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _safe_commit(db: AsyncSession) -> bool:
        """
        Commit que trata IntegrityError da constraint única de webhook_logs
        como caso benigno de duplicidade (dois webhooks idênticos processados
        quase simultaneamente, escapando da checagem already_processed).
        Retorna True se comitou, False se era duplicado (já rolou back).
        Qualquer outro erro é propagado normalmente.
        """
        try:
            await WebhookService._safe_commit(db)
            return True
        except IntegrityError:
            await db.rollback()
            logger.info("Webhook duplicado (corrida) — ignorando com segurança.")
            return False

    @staticmethod
    async def mark_webhook_error(
        db: AsyncSession,
        topic: str | None,
        resource_id: str | None,
        params: dict,
        data: dict,
        message: str,
    ) -> None:
        await db.rollback()

        error_log = WebhookLog(
            topic=topic or "unknown",
            resource_id=resource_id,
            payload={"query_params": params, "body": data},
            status=WebhookStatus.error,
            error_message=message[:255],
        )
        db.add(error_log)
        await db.commit()

    @staticmethod
    async def webhook(request: Request, db: AsyncSession = Depends(get_db), sdk: mercadopago.SDK = Depends(get_mp_sdk)):
        params = dict(request.query_params)
        try:
            data = await request.json()
        except(json.JSONDecodeError, ValueError):
            data = {}
            logger.warning("Webhook recebido sem JSON válido.")

        # Verifica o tipo de request - se é pagamento ou preapproval
        topic = data.get("type") or params.get("topic") or data.get("topic")
        resource_id = (data.get("data", {}).get("id") or params.get("data.id") or params.get("id") or data.get("resource"))

        logger.info(f"Processando Webhook - Topic: {topic}, Resource ID: {resource_id}")

        x_signature = request.headers.get("x-signature", "")
        x_request_id = request.headers.get("x-request-id", "")
        mp_secret = settings.MP_WEBHOOK_SECRET
        if not mp_secret:
            logger.error("MP_WEBHOOK_SECRET não configurado — rejeitar todos os webhooks até corrigir")
            return JSONResponse({"status": "misconfigured"}, status_code=500)
    
        if not WebhookService.verify_mp_signature(x_signature, x_request_id, str(resource_id or ""), mp_secret):
            logger.warning(
                f"Assinatura inválida — topic={topic}, resource_id={resource_id}, "
                f"x-request-id={x_request_id}"
            )
            # 401 aqui é seguro: o MP não reencaminha se receber 401
            return JSONResponse({"status": "unauthorized"}, status_code=401)
    

        if await WebhookService.already_processed(db, topic, str(resource_id)):
            return JSONResponse({"status": "duplicate"}, status_code=200)
        
        webhook_log = WebhookLog(
            topic=topic or "unknown",
            resource_id=str(resource_id) if resource_id else None,
            payload={"query_params": params, "body": data},
            status=WebhookStatus.processing,
        )
        try:
            db.add(webhook_log)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return JSONResponse({"status": "duplicate"}, status_code=200)

        if not resource_id:
            webhook_log.status = WebhookStatus.ignored
            webhook_log.error_message = "Sem resource_id."
            logger.info("Webhook ignorado: Sem resource_id.")
            await WebhookService._safe_commit(db)
            return JSONResponse({"status": "ignored"}, status_code=200)

        # Mensalidade cobrada no cartão
        if topic == "payment":
            try:
                payment_info = await mp_call(sdk.payment().get, resource_id)
                if payment_info.get("status") == 404:
                    webhook_log.status = WebhookStatus.ignored
                    webhook_log.error_message = "Pagamento não encontrado."
                    await WebhookService._safe_commit(db)                
                    return JSONResponse(content={"status": "ignored"}, status_code=200)
                
                if payment_info.get("status") not in [200, 201]:
                    raise ValueError(f"Erro em pagamento no MP: {payment_info}")
                
                payment_data = payment_info.get("response", {})
                current_status = payment_data.get("status")
                external_reference = payment_data.get("external_reference") 

                # Verifica o subscription_id com base na external_reference passada na variável payment_data
                try:
                    my_subscription_id = int(external_reference) if external_reference else None
                except (ValueError, TypeError):
                    my_subscription_id = None
                    logger.warning("External reference inválido")

                if my_subscription_id:
                    # Busca pela assinatura no banco
                    stmt = select(Subscription).options(selectinload(Subscription.plan)).filter(Subscription.id == int(my_subscription_id))
                    result = await db.execute(stmt)
                    db_subscription = result.scalars().first()

                    if db_subscription:
                        now = datetime.now(timezone.utc)
                        if current_status == "approved":
                            current_end = getattr(db_subscription, "end_date", None)

                            if db_subscription.status == SubscriptionStatus.incomplete:
                                db_subscription.initial_date = now

                            plano_enum = db_subscription.plan.period.value if db_subscription.plan else PlanPeriod.monthly.value
                            add_time = PERIOD_DELTA.get(plano_enum, relativedelta(months=1))

                            # Atualiza a end_date da assinatura
                            base_date = current_end if (current_end and current_end > now) else now
                            db_subscription.end_date = base_date + add_time
                            db_subscription.status = SubscriptionStatus.active

                            logger.info(f"Assinatura renovada até {db_subscription.end_date}")
                        
                        elif current_status in ["rejected", "cancelled", "refunded"]:
                            db_subscription.status = SubscriptionStatus.canceled
                            if not db_subscription.end_date:
                                db_subscription.end_date = now
                        
                webhook_log.status = WebhookStatus.success
                await WebhookService._safe_commit(db)
                return JSONResponse({"status": "success"}, status_code=200)
            
            except Exception as e:
                logger.exception(f"Erro ao processar pagamento {resource_id}")
                await WebhookService.mark_webhook_error(
                    db=db,
                    topic=topic,
                    resource_id=str(resource_id) if resource_id else None,
                    params=params,
                    data=data,
                    message=str(e),
                )
                return JSONResponse(
                    content={"status": "error", "message": "Erro interno"},
                    status_code=200
                )

        # Alteração de assinatura
        # O preapproval só ativa/atualiza o status da assinatura
        # O end_date é alterado em payment para evitar dobrar o período de uso do sistema,
        # pois o MP envia webhooks de preapproval e payment quase simultâneos no ato da assinatura
        elif topic == "preapproval":
            try:
                sub_info = await mp_call(sdk.preapproval().get, resource_id)
                if sub_info.get("status") == 404:
                    webhook_log.status = WebhookStatus.ignored
                    webhook_log.error_message = "Preapproval não encontrado."
                    await WebhookService._safe_commit(db)
                    return JSONResponse({"status": "ignored"}, status_code=200)
                
                if sub_info.get("status") not in [200, 201]:
                    raise ValueError(f"Erro no preapproval do Mercado Pago: {sub_info}")

                sub_data = sub_info.get("response", {}) or {}
                current_status = sub_data.get("status")
                external_reference = sub_data.get("external_reference")

                # Verifica o subscription_id com base na external_reference passada na variável sub_data
                try:
                    my_subscription_id = int(external_reference) if external_reference else None
                except (ValueError, TypeError):
                    my_subscription_id = None
                    logger.warning("External reference inválido")

                if my_subscription_id:
                    now = datetime.now(timezone.utc)
                    # Busca a assinatura no banco
                    stmt = select(Subscription).options(selectinload(Subscription.plan)).filter(Subscription.id == int(my_subscription_id))
                    result = await db.execute(stmt)
                    db_subscription = result.scalars().first()

                    if db_subscription:
                    # Altera o status da assinatura com base no status do MP
                        if current_status == "authorized":
                            if db_subscription.status == SubscriptionStatus.incomplete:
                                db_subscription.initial_date = now

                            db_subscription.status = SubscriptionStatus.active
                            logger.info(f"Assinatura {my_subscription_id} ativada via preapproval")

                        elif current_status in ["cancelled", "paused"]:
                            db_subscription.status = SubscriptionStatus.canceled
                            db_subscription.end_date = now
                
                webhook_log.status = WebhookStatus.success
                await WebhookService._safe_commit(db)
                return JSONResponse({"status": "success"}, status_code=200)
            
            except Exception as e:
                logger.exception(f"Erro ao processar assinatura {resource_id}")
                await WebhookService.mark_webhook_error(
                    db=db,
                    topic=topic,
                    resource_id=str(resource_id) if resource_id else None,
                    params=params,
                    data=data,
                    message=str(e),
                )
                return JSONResponse(
                    content={"status": "error", "message": "Erro interno"},
                    status_code=200
                )
        else:
            # Mensagem para informar que o webhook ainda não foi entregue
            webhook_log.status = WebhookStatus.ignored
            webhook_log.error_message = "Webhook ainda não entregue."
            await WebhookService._safe_commit(db)
            logger.info("Tópico de webhook ainda não entregue.", extra={"topic": topic, "resource_id": resource_id})
        return JSONResponse(content={"status": "success"}, status_code=200)
