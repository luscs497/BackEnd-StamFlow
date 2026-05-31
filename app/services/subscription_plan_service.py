from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select, and_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.subscription_plan import SubscriptionPlanCreate

class SubscriptionPlanService:
    @staticmethod
    async def register_subscription_plan(session: AsyncSession, data: SubscriptionPlanCreate) -> SubscriptionPlan:

        new_subscription_plan = SubscriptionPlan(
            name=data.name,
            description=data.description,
            price_in_cents=data.price_in_cents,
            type=data.type,
            period=data.period,
        )

        session.add(new_subscription_plan)
        try:
            await session.commit()
            await session.refresh(new_subscription_plan)
            return new_subscription_plan
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao tentar salvar o plano."
            )
    
    @staticmethod
    async def read_plans(session: AsyncSession):
        try:
            result = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True))
            plans = result.scalars().all()
            return plans
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao buscar planos."
            )
        
    @staticmethod
    async def read_plan(session: AsyncSession, plan_id: int):
        try:
            result = await session.execute(
                select(SubscriptionPlan)
                .where(SubscriptionPlan.id == plan_id)
                .where(SubscriptionPlan.is_active == True)
                )
            plan = result.scalars().one_or_none()
            if not plan:
                raise HTTPException(
                status_code=404,
                detail="Nenhum plano foi encontrado."
            )
            return plan
        except SQLAlchemyError:
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao buscar plano."
            )
    
    @staticmethod
    async def update_subscription_plan(plan_id: int, subscription_data, session: AsyncSession):
        # Verifica se o plan_id do schema corresponde a um plano no banco
        plan = await session.get(SubscriptionPlan, plan_id)
        if not plan:
            raise HTTPException(
                status_code=404,
                detail="Nenhum plano foi encontrado."
            )
        
        # Alterações no banco
        if subscription_data.name:
            plan.name = subscription_data.name

        if subscription_data.description:
            plan.description = subscription_data.description

        if subscription_data.price_in_cents is not None:
            plan.price_in_cents = subscription_data.price_in_cents

        if subscription_data.type:
            plan.type = subscription_data.type
        
        if subscription_data.period:
            plan.period = subscription_data.period
        
        if subscription_data.is_active is not None:
            plan.is_active = subscription_data.is_active

        session.add(plan)  
        try:        
            await session.commit()
            await session.refresh(plan)
            return plan
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao tentar atualizar o plano."
            )

    @staticmethod
    async def delete_subscription_plan(session: AsyncSession, subscription_plan_id: int):
        # SOFT DELETE
        subscription_plan = await session.get(SubscriptionPlan, subscription_plan_id)
        if not subscription_plan:
            raise HTTPException(
                status_code=404,
                detail="Nenhum plano foi encontrado."
            )
        
        # Torna o plano desativo no banco
        subscription_plan.is_active = False
        session.add(subscription_plan)
        try:
            await session.commit()
            return {"message": "Plano desativado com sucesso."}
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao excluir o plano."
            )