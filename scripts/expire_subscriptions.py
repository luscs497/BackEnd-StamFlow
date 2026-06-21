"""
Job de expiração de trials/licenças do StamFlow.

Marca como CANCELED as assinaturas vencidas (end_date < agora) que estão em
TRIALING ou ACTIVE e que NÃO são gerenciadas pelo MercadoPago (mp_subscription_id
nulo) — ou seja, testes grátis e licenças empresariais provisionadas manualmente.
Assinaturas com mp_subscription_id são deixadas para o webhook/MercadoPago gerenciar
(evita conflito com renovação automática).

Observação: o acesso já é cortado em tempo de request pelo check_active_subscription;
este job é higiene de dados/relatório.

Rodar manual:
    cd /opt/apps/stamflow-api && .venv/bin/python scripts/expire_subscriptions.py
Idempotente: se nada venceu, não altera nada.
"""
import os
import sys
import asyncio
from datetime import datetime, timezone

# raiz do projeto no path (permite "import app.*" rodando de qualquer lugar)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# importa todos os models para resolver as relationships entre eles
from app.models import (  # noqa: F401
    company, client, manager, client_token, client_achievement,
    ticket, ticket_message, daily_report, subscription,
    subscription_plan, webhook, invite, enterprise_request,
)

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription, SubscriptionStatus


async def main():
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.end_date.is_not(None),
                Subscription.end_date < now,
                Subscription.status.in_([
                    SubscriptionStatus.trialing,
                    SubscriptionStatus.active,
                ]),
                Subscription.mp_subscription_id.is_(None),
            )
        )
        vencidas = result.scalars().all()
        for sub in vencidas:
            sub.status = SubscriptionStatus.canceled
        await db.commit()
        print(f"[{now.isoformat()}] expiradas: {len(vencidas)} assinatura(s) -> CANCELED.")


if __name__ == "__main__":
    asyncio.run(main())
