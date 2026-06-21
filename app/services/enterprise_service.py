from decimal import Decimal
from datetime import datetime, timezone
from urllib.parse import quote

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise_request import EnterpriseRequest, EnterpriseRequestStatus
from app.models.subscription_plan import SubscriptionPlan, PlanType, PlanPeriod
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.company import Company
from app.schemas.enterprise import EnterpriseRequestCreate, EnterpriseProvision

# +55 84 8200-2100 (apenas dígitos, padrão internacional do wa.me).
# Ajuste aqui se o número/dígitos mudarem.
WHATSAPP_NUMBER = "558482002100"

PERIOD_DELTA = {
    PlanPeriod.monthly.value: relativedelta(months=1),
    PlanPeriod.quarterly.value: relativedelta(months=3),
    PlanPeriod.semiannual.value: relativedelta(months=6),
    PlanPeriod.annual.value: relativedelta(years=1),
}


def _whatsapp_link(req: EnterpriseRequest) -> str:
    msg = (
        "Olá! Tenho interesse no plano empresarial do StamFlow.\n"
        f"Empresa: {req.nome_empresa}\n"
        f"Colaboradores: {req.qtd_colaboradores}\n"
        f"Licenças de gestor: {req.qtd_gestores}\n"
        f"Contato: {req.contato_nome}"
    )
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(msg)}"


class EnterpriseService:
    @staticmethod
    async def create_request(session: AsyncSession, data: EnterpriseRequestCreate) -> dict:
        """Cria o pedido no funil (status pendente_proposta) e devolve o link do WhatsApp."""
        req = EnterpriseRequest(
            nome_empresa=data.nome_empresa,
            contato_nome=data.contato_nome,
            contato_email=data.contato_email,
            contato_whatsapp=data.contato_whatsapp,
            qtd_colaboradores=data.qtd_colaboradores,
            qtd_gestores=data.qtd_gestores,
            observacoes=data.observacoes,
            status=EnterpriseRequestStatus.pendente_proposta,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        return {
            "message": "Solicitação registrada. Fale com nosso time para fechar a proposta.",
            "request_id": req.id,
            "whatsapp_url": _whatsapp_link(req),
        }

    @staticmethod
    async def list_requests(session: AsyncSession, status=None):
        q = select(EnterpriseRequest).order_by(EnterpriseRequest.id.desc())
        if status is not None:
            q = q.where(EnterpriseRequest.status == status)
        res = await session.execute(q)
        return res.scalars().all()

    @staticmethod
    async def get_request(session: AsyncSession, request_id: int) -> EnterpriseRequest:
        req = await session.get(EnterpriseRequest, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
        return req

    @staticmethod
    async def update_status(session: AsyncSession, request_id: int, new_status) -> EnterpriseRequest:
        req = await EnterpriseService.get_request(session, request_id)
        req.status = new_status
        await session.commit()
        await session.refresh(req)
        return req

    @staticmethod
    async def provision(session: AsyncSession, request_id: int, data: EnterpriseProvision) -> dict:
        """
        Provisiona o plano empresarial aprovado: cria uma Subscription ATIVA para a
        empresa (já cadastrada), com N licenças de colaborador + M de gestor vindas
        do pedido, e marca o pedido como 'provisionado'.
        """
        req = await EnterpriseService.get_request(session, request_id)

        plan = await session.get(SubscriptionPlan, data.plan_id)
        if not plan or plan.type != PlanType.corporative:
            raise HTTPException(status_code=400, detail="Informe um plano corporativo válido.")

        company = await session.get(Company, data.company_id)
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Empresa não encontrada. Cadastre a empresa (/company/register) antes de provisionar."
            )

        # Não duplica assinatura ativa da mesma empresa
        existing = await session.execute(
            select(Subscription).where(
                Subscription.company_id == company.id,
                Subscription.status == SubscriptionStatus.active,
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Esta empresa já possui uma assinatura ativa.")

        now = datetime.now(timezone.utc)
        period_key = plan.period.value if hasattr(plan.period, "value") else plan.period
        delta = PERIOD_DELTA.get(period_key, relativedelta(months=1))

        licenses = req.qtd_colaboradores + req.qtd_gestores
        total_cents = plan.price_in_cents * licenses

        sub = Subscription(
            plan_id=plan.id,
            company_id=company.id,
            status=SubscriptionStatus.active,
            end_date=now + delta,
            license_quantity=licenses,
            price_at_purchase=Decimal(total_cents) / Decimal(100),
            max_managers_purchased=req.qtd_gestores,
            max_employees_purchased=req.qtd_colaboradores,
        )
        session.add(sub)
        req.company_id = company.id
        req.status = EnterpriseRequestStatus.provisionado
        await session.commit()
        await session.refresh(sub)

        return {
            "message": "Empresa provisionada com sucesso.",
            "company_id": company.id,
            "subscription_id": sub.id,
            "licencas": {"gestores": req.qtd_gestores, "colaboradores": req.qtd_colaboradores},
            "expira_em": sub.end_date.isoformat(),
            "painel_gestor": "https://gestor.stamflow.com.br/",
        }
