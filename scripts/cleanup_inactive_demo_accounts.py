"""
Job de limpeza de contas DEMO inativas do StamFlow.

Remove contas Client cuja ÚNICA subscription seja status DEMO (já expirada
ou não) E que estejam inativas (last_activity_at) há mais de 90 dias.

Por que só contas 100% demo: uma conta que converteu para assinatura paga
(ACTIVE) ou trial completo (TRIALING) NUNCA deve ser removida por este job,
mesmo que a subscription DEMO antiga ainda exista no histórico. O filtro usa
a subscription MAIS RECENTE da conta (mesmo critério de outras partes do
código, ex.: subscription_service.start_trial) — se a mais recente não for
DEMO, a conta é poupada.

Cascade: Client tem cascade="all, delete-orphan" em reports e notifications
(ver app/models/client.py), então excluir o Client já remove os daily_reports
e notifications dele automaticamente. A Subscription tem
ForeignKey(..., ondelete="CASCADE") para client_id, então também é removida
junto pelo próprio banco.

Rodar manual (mesmo padrão de scripts/expire_subscriptions.py):
    cd /opt/apps/stamflow-api && .venv/bin/python scripts/cleanup_inactive_demo_accounts.py
Idempotente: se nada está inativo há 90+ dias, não altera nada.

Sugestão de agendamento (mesmo padrão dos outros jobs, 1x/dia):
    systemd timer diário, ou:
    0 5 * * * cd /opt/apps/stamflow-api && .venv/bin/python scripts/cleanup_inactive_demo_accounts.py
"""
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

# raiz do projeto no path (permite "import app.*" rodando de qualquer lugar)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# importa todos os models para resolver as relationships entre eles
# (mesmo motivo do expire_subscriptions.py: sem importar 'notification',
# o SQLAlchemy falha ao configurar o mapper do Client).
from app.models import (  # noqa: F401
    company, client, manager, client_token, client_achievement,
    ticket, ticket_message, daily_report, subscription,
    subscription_plan, webhook, invite, enterprise_request, notification,
)

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal
from app.models.client import Client
from app.models.subscription import Subscription, SubscriptionStatus

INACTIVITY_DAYS = 90


async def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=INACTIVITY_DAYS)

    async with AsyncSessionLocal() as db:
        # Candidatas: clients sem company_id (conta individual/demo nunca é
        # de colaborador de empresa) e inativas há mais de 90 dias.
        result = await db.execute(
            select(Client)
            .options(selectinload(Client.subscription))
            .where(
                Client.company_id.is_(None),
                Client.last_activity_at.is_not(None),
                Client.last_activity_at < cutoff,
            )
        )
        candidatas = result.scalars().all()

        removidas = 0
        for c in candidatas:
            sub = c.subscription
            # Só remove se a (única/mais recente) subscription for DEMO.
            # Conta sem subscription nenhuma não é alvo deste job (não é
            # um cenário esperado para conta criada via /demo/signup, mas
            # por segurança não tocamos nela).
            if sub is not None and sub.status == SubscriptionStatus.demo:
                await db.delete(c)
                removidas += 1

        await db.commit()
        print(f"[{now.isoformat()}] limpeza demo: {removidas} conta(s) inativa(s) removida(s) "
              f"(inatividade > {INACTIVITY_DAYS} dias).")


if __name__ == "__main__":
    asyncio.run(main())
