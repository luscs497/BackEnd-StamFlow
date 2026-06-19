"""
Seed dos planos AVULSOS (individuais) — PREÇOS PROVISÓRIOS.
Rode UMA vez:  .venv/bin/python scripts/seed_plans.py
É idempotente: se um plano com o mesmo nome já existir, ele pula.
Troque os preços (price_in_cents) quando definir os valores reais.
"""
import os
import sys
import asyncio

# Garante que a raiz do projeto está no path (permite "import app.*"
# rodando o script de qualquer lugar, sem precisar de PYTHONPATH).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# IMPORTANTE: importar TODOS os models antes de consultar, para o SQLAlchemy
# conseguir resolver as relationships entre eles (ex.: SubscriptionPlan -> Subscription).
from app.models import (  # noqa: F401
    company, client, manager, client_token, client_achievement,
    ticket, ticket_message, daily_report, subscription,
    subscription_plan, webhook, invite, enterprise_request,
)

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.subscription_plan import SubscriptionPlan, PlanType, PlanPeriod

# price_in_cents = preço em CENTAVOS (R$ 29,90 -> 2990). PROVISÓRIO.
PLANOS_AVULSOS = [
    {"name": "Avulso Mensal",     "period": PlanPeriod.monthly,    "price_in_cents": 2990,  "description": "Plano individual mensal (PROVISORIO)"},
    {"name": "Avulso Trimestral", "period": PlanPeriod.quarterly,  "price_in_cents": 7990,  "description": "Plano individual trimestral (PROVISORIO)"},
    {"name": "Avulso Semestral",  "period": PlanPeriod.semiannual, "price_in_cents": 14990, "description": "Plano individual semestral (PROVISORIO)"},
    {"name": "Avulso Anual",      "period": PlanPeriod.annual,     "price_in_cents": 26990, "description": "Plano individual anual (PROVISORIO)"},
]


async def main():
    async with AsyncSessionLocal() as db:
        criados = 0
        for p in PLANOS_AVULSOS:
            existe = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.name == p["name"])
            )
            if existe.scalars().first():
                print(f"[skip] já existe: {p['name']}")
                continue
            db.add(SubscriptionPlan(type=PlanType.individual, is_active=True, **p))
            criados += 1
            print(f"[novo] {p['name']} - R$ {p['price_in_cents']/100:.2f}")
        await db.commit()
        print(f"OK: {criados} plano(s) criado(s).")


if __name__ == "__main__":
    asyncio.run(main())
