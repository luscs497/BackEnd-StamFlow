from typing import Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.manager import Manager
from app.models.company import Company
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.panel_links import panels_for_user


def _enum_val(v):
    return v.value if hasattr(v, "value") else v


class AccountService:
    @staticmethod
    async def get_profile(session: AsyncSession, user: Any) -> dict:
        """
        Visão consolidada da conta: dados, assinatura/licença atual,
        situação do teste grátis e os links dos painéis liberados.
        """
        # ---- dados da conta (nome varia por tipo) ----
        if isinstance(user, Client):
            tipo, nome = "client", user.nome_completo
        elif isinstance(user, Manager):
            tipo, nome = "manager", user.nome
        elif isinstance(user, Company):
            tipo, nome = "company", user.nome_fantasia
        else:
            tipo, nome = "desconhecido", None

        conta = {
            "id": user.id,
            "nome": nome,
            "email": getattr(user, "email", None),
            "tipo": tipo,
        }
        if isinstance(user, Client):
            conta["cpf"] = user.cpf
            conta["telefone"] = user.telefone
            conta["criado_em"] = user.criado_em.isoformat() if user.criado_em else None

        # ---- ids para localizar a assinatura (própria ou da empresa) ----
        client_id = user.id if isinstance(user, Client) else None
        if isinstance(user, Company):
            company_id = user.id
        else:
            company_id = getattr(user, "company_id", None)

        conds = []
        if client_id is not None:
            conds.append(Subscription.client_id == client_id)
        if company_id is not None:
            conds.append(Subscription.company_id == company_id)

        assinatura = None
        sub_status_atual = None  # usado por panels_for_user para decidir o link do painel demo
        if conds:
            res = await session.execute(
                select(Subscription)
                .options(selectinload(Subscription.plan))
                .where(or_(*conds))
                .order_by(Subscription.id.desc())
            )
            sub = res.scalars().first()
            if sub:
                sub_status_atual = _enum_val(sub.status)
                plano = None
                if sub.plan:
                    plano = {
                        "nome": sub.plan.name,
                        "tipo": _enum_val(sub.plan.type),
                        "periodo": _enum_val(sub.plan.period),
                    }
                assinatura = {
                    "status": _enum_val(sub.status),
                    "em_trial": sub.status == SubscriptionStatus.trialing,
                    "inicio": sub.initial_date.isoformat() if sub.initial_date else None,
                    "expira_em": sub.end_date.isoformat() if sub.end_date else None,
                    "licencas": sub.license_quantity,
                    "preco_pago": float(sub.price_at_purchase) if sub.price_at_purchase is not None else None,
                    "plano": plano,
                }

        # ---- teste grátis (só faz sentido para client) ----
        trial = None
        if isinstance(user, Client):
            trial = {
                "ja_usou": user.trial_used_at is not None,
                "usado_em": user.trial_used_at.isoformat() if user.trial_used_at else None,
            }

        return {
            "conta": conta,
            "assinatura": assinatura,
            "trial": trial,
            # CORREÇÃO: passa o status da subscription para que conta DEMO
            # receba o link do painel demo (demo.stamflow.com.br), não o do
            # painel avulso pagante.
            "paineis": panels_for_user(user, subscription_status=sub_status_atual),
        }
