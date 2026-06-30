from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.models.client import Client
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.subscription_plan import SubscriptionPlan, PlanType
from app.schemas.demo import DemoSignupRequest
from app.services.utils import is_email_in_use, is_cpf_in_use
from app.core.security import hash_password


class DemoService:
    @staticmethod
    async def signup_demo(session: AsyncSession, data: DemoSignupRequest) -> dict:
        """
        Cria a conta + ativa a versão DEMO de 7 dias (decisão de produto,
        2026-06): limitada, sem cartão, CPF obrigatório como único freio
        contra contas ilimitadas.

        Regras de unicidade (1 demo por pessoa):
          - clients.cpf é UNIQUE no banco -> tentar criar 2ª conta com o
            mesmo CPF falha na constraint (capturamos e devolvemos 400 claro,
            em vez de vazar IntegrityError genérico).
          - clients.email também é UNIQUE (verificado explicitamente abaixo
            para mensagem de erro mais específica que a do CPF).
          - demo_used_at não nasce setado aqui porque a conta é nova; existe
            para impedir reiniciar o demo numa conta que já o usou (rota
            futura, se algum dia o demo puder ser "reativado" manualmente).
        """
        if await is_email_in_use(session, data.email):
            raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

        if await is_cpf_in_use(session, data.cpf):
            raise HTTPException(
                status_code=400,
                detail="Este CPF já utilizou o período de demonstração gratuita.",
            )

        # Plano-base do demo: o plano individual ativo mais barato (mesmo
        # critério usado em start_trial), só para a Subscription ter um
        # plan_id válido (FK obrigatória) — price_at_purchase fica 0.00.
        plan_result = await session.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.type == PlanType.individual,
                SubscriptionPlan.is_active.is_(True),
            )
            .order_by(SubscriptionPlan.price_in_cents.asc())
        )
        base_plan = plan_result.scalars().first()
        if not base_plan:
            raise HTTPException(
                status_code=500,
                detail="Nenhum plano individual disponível para a demonstração.",
            )

        now = datetime.now(timezone.utc)

        new_client = Client(
            nome_completo=data.nome_completo,
            cpf=data.cpf,
            email=data.email,
            senha_hash=hash_password(data.senha),
            demo_used_at=now,
            last_activity_at=now,
        )
        session.add(new_client)
        await session.flush()  # garante new_client.id antes de criar a Subscription

        demo_subscription = Subscription(
            plan_id=base_plan.id,
            client_id=new_client.id,
            status=SubscriptionStatus.demo,
            end_date=now + timedelta(days=7),
            license_quantity=1,
            price_at_purchase=Decimal("0.00"),
            max_managers_purchased=0,
            max_employees_purchased=0,
        )
        session.add(demo_subscription)

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            # Rede de segurança contra corrida (duas requisições simultâneas
            # com o mesmo CPF/email passando pela checagem acima ao mesmo
            # tempo) — a constraint UNIQUE do banco pega o que a checagem
            # em Python não pegou a tempo.
            raise HTTPException(
                status_code=400,
                detail="Este e-mail ou CPF já está cadastrado.",
            )

        await session.refresh(new_client)
        await session.refresh(demo_subscription)

        return {
            "client_id": new_client.id,
            "email": new_client.email,
            "demo_expira_em": demo_subscription.end_date.isoformat(),
        }
