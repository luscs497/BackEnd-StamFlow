from fastapi import HTTPException

from app.models.company import Company
from app.models.client import Client
from app.models.subscription_plan import SubscriptionPlan, PlanType, PlanPeriod
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.subscription import SubscriptionCheckoutRequest, SubscriptionUpdate
from app.services.utils import mp_call

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import selectinload
from typing import Any
import mercadopago
from decimal import Decimal
from datetime import datetime, timezone

class SubscriptionService:
    @staticmethod
    async def process_checkout(session: AsyncSession, data: SubscriptionCheckoutRequest, user: Any, sdk: mercadopago.SDK) -> dict:            
        # Busca pelo plano no banco com mesmo id passado pelo schema
        plan = await session.get(SubscriptionPlan, data.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="O plano informado não existe.")
        
        client_id = None
        company_id = None
        
        if isinstance(user, Client):
            client_id = user.id
            if plan.type != PlanType.individual:
                raise HTTPException(
                    status_code=400,
                    detail="O tipo de usuário requer escolher um plano individual."
                )
            
            query = (
                select(Subscription)
                .where(user.id == Subscription.client_id)
                .order_by(Subscription.id.desc())
                    )
            result = await session.execute(query)
            existing_subscription = result.scalars().first()

            if existing_subscription:
                # Caso a Subscription tenha status ACTIVE
                if existing_subscription.status == SubscriptionStatus.active:
                    raise HTTPException(
                        status_code=400,
                        detail="O usuário já possui uma assinatura ativa."
                    )
                
                # Caso haja uma Subscription com status INCOMPLETE
                elif existing_subscription.status == SubscriptionStatus.incomplete:
                    if existing_subscription.plan_id == plan.id:
                        mp_id = existing_subscription.mp_subscription_id
                        # Busca os dados no Mercado Pago
                        mp_response = await mp_call(sdk.preapproval().get, mp_id)
                        if mp_response.get("status") == 200:
                            # Extrai o link de pagamento
                            checkout_url = mp_response["response"]["init_point"]
                            return {
                                "message": "Você já tem um processo de assinatura em andamento.",
                                "url": checkout_url
                            }   
                        else:
                            if existing_subscription.mp_subscription_id:
                                try:
                                    await mp_call(sdk.preapproval().update, existing_subscription.mp_subscription_id, {"status": "cancelled"})
                                except Exception:
                                    raise HTTPException(
                                        status_code=500,
                                        detail="Erro interno"
                                    )
                            await session.delete(existing_subscription)
                            await session.flush()
                    else:
                        if existing_subscription.mp_subscription_id:
                            try:
                                await mp_call(sdk.preapproval().update, existing_subscription.mp_subscription_id, {"status": "cancelled"})
                            except Exception:
                                raise HTTPException(
                                    status_code=500,
                                    detail="Erro interno"
                                )

                        await session.delete(existing_subscription)
                        await session.flush()
                
        elif isinstance(user, Company):
            company_id = user.id
            if plan.type != PlanType.corporative:
                raise HTTPException(
                    status_code=400,
                    detail="O tipo de usuário requer escolher um plano corporativo."
                )
            
            query = (
                select(Subscription)
                .where(user.id == Subscription.company_id)
                .order_by(Subscription.id.desc())
                    )
            
            result = await session.execute(query)
            existing_subscription = result.scalars().first()

            if existing_subscription:
                # Caso a Subscription tenha status ACTIVE
                if existing_subscription.status == SubscriptionStatus.active:
                    raise HTTPException(
                        status_code=400,
                        detail="A empresa já possui uma assinatura ativa."
                    )
                # Caso haja uma Subscription com status INCOMPLETE
                elif existing_subscription.status == SubscriptionStatus.incomplete:
                    req_managers = data.managers_quantity if data.managers_quantity else 0
                    req_employees = data.employees_quantity if data.employees_quantity else 0
                    
                    # Verifica se a quantidade de licensas é igual à anterior
                    is_same_qty = (
                        existing_subscription.plan_id == plan.id and
                        existing_subscription.max_managers_purchased == req_managers and
                        existing_subscription.max_employees_purchased == req_employees
                    )

                    # Se as quantidades são iguais, retorna a URL antiga
                    if is_same_qty:
                        mp_id = existing_subscription.mp_subscription_id
                        # Busca os dados no Mercado Pago
                        mp_response = await mp_call(sdk.preapproval().get, mp_id)
                        if mp_response.get("status") == 200:
                            # Extrai o link de pagamento
                            checkout_url = mp_response["response"]["init_point"]
                            return {
                                "message": "Você já tem um processo de assinatura em andamento.",
                                "url": checkout_url
                            }
                        else:
                            if existing_subscription.mp_subscription_id:
                                try:
                                    await mp_call(sdk.preapproval().update, existing_subscription.mp_subscription_id, {"status": "cancelled"})
                                except Exception:
                                    raise HTTPException(status_code=500, detail="Erro interno")
                            await session.delete(existing_subscription)
                            await session.flush()
                        
                    else:
                        if existing_subscription.mp_subscription_id:
                            try:
                                await mp_call(sdk.preapproval().update, existing_subscription.mp_subscription_id, {"status": "cancelled"})
                            except Exception:
                                raise HTTPException(
                                    status_code=500,
                                    detail="Erro interno"
                                )

                        await session.delete(existing_subscription)
                        await session.flush()

                                
        else:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não pode realizar essa operação."
            )
            
        total_price_cents = plan.price_in_cents # Preço base padrão
        licenses = 1
        max_managers = 0
        max_employees = 0

        if plan.type == PlanType.corporative:
            if data.managers_quantity == 0 and data.employees_quantity == 0:
                raise HTTPException(status_code=400, detail="Selecione pelo menos 1 licença para prosseguir.")
            
            max_managers = data.managers_quantity
            max_employees = data.employees_quantity
            licenses = max_managers + max_employees

            total_price_cents = plan.price_in_cents * licenses

        new_subscription = Subscription(
            plan_id=plan.id,
            max_managers_purchased=max_managers,
            max_employees_purchased=max_employees,
            license_quantity=licenses,
            price_at_purchase=Decimal(total_price_cents) / Decimal(100),
            client_id=client_id,
            company_id=company_id,
            status=SubscriptionStatus.incomplete # Começa como incompleto
        )
        session.add(new_subscription)
        await session.flush()

        # Reforço que as variáveis são do tipo int
        price = int(plan.price_in_cents)
        total_price = round((licenses * price) / 100, 2)
        mp_frequency_map = {
            PlanPeriod.monthly: 1,
            PlanPeriod.quarterly: 3,
            PlanPeriod.semiannual: 6,
            PlanPeriod.annual: 12,
        }

        mp_frequency = mp_frequency_map.get(plan.period, 1)

        subscription_data = {
            "reason": f"Assinatura {plan.name}",
            "external_reference": str(new_subscription.id),
            "payer_email": user.email,
            "back_url": "https://login.stamflow.com.br",
            "status": "pending",
            "auto_recurring": {
                "frequency": mp_frequency,
                "frequency_type": "months",
                "transaction_amount": total_price,
                "currency_id": "BRL",
            },
        }
        # Registra a assinatura no MP passando o dict
        try:
            result = await mp_call(sdk.preapproval().create, subscription_data)
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar assinatura no Mercado Pago: {str(e)}."
            )
        
        # Recebe resposta do MP
        mp_response = result.get("response", {}) if isinstance(result, dict) else {}
        checkout_url = mp_response.get("init_point")

        if result.get("status") not in [200, 201] or not checkout_url:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail={"message": "Erro do Mercado Pago ao criar assinatura", "mp_response": mp_response}
            )
        
        new_subscription.mp_subscription_id = mp_response.get("id")

        await session.commit()
        await session.refresh(new_subscription)

        return {
            "message": "Assinatura ativada com sucesso!",
            "subscription_id": new_subscription.id,
            "checkout_url": checkout_url,
            "status": mp_response.get("status")
        }
    
    @staticmethod
    async def read_subscription(session: AsyncSession, current_user: Any) -> Subscription:
        if isinstance(current_user, Client):
            query = (
                select(Subscription)
                .where(current_user.id == Subscription.client_id)
                .order_by(Subscription.id.desc())
                .options(selectinload(Subscription.plan))
                    )
        elif isinstance(current_user, Company):
            query = (
                select(Subscription)
                .where(current_user.id == Subscription.company_id)
                .order_by(Subscription.id.desc())
                .options(selectinload(Subscription.plan))
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de usuário inválido."
            )
        result = await session.execute(query)
        subscription = result.scalars().first()

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma assinatura foi encontrada."
            )
        return subscription
    
    @staticmethod
    async def update_subscription(session: AsyncSession, subscription_data: SubscriptionUpdate, user: Any, sdk: mercadopago.SDK) -> Subscription:

        if isinstance(user, Client):
            query = (
                select(Subscription)
                .where(Subscription.client_id == user.id)
                .order_by(Subscription.id.desc())
                .options(selectinload(Subscription.plan))
            )
        elif isinstance(user, Company):
            query = (
                select(Subscription)
                .where(Subscription.company_id == user.id)
                .order_by(Subscription.id.desc())
                .options(selectinload(Subscription.plan))
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de usuário inválido."
            )

        result = await session.execute(query)
        subscription = result.scalars().first()

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma assinatura foi encontrada."
            )
        
        # Permitir atualizar somente Assinaturas com status ativo/teste grátis
        if subscription.status not in [SubscriptionStatus.active, SubscriptionStatus.trialing]:
            raise HTTPException(status_code=400, detail="Apenas assinaturas ativas podem ser alteradas.")

        plan = subscription.plan
        if not plan:
            raise HTTPException(
                status_code=404,
                detail="Plano vinculado à assinatura não encontrado."
            )

        # Checagem dos tipos de plano para verificar se tem acesso a atualizar
        if plan.type == PlanType.corporative and not isinstance(user, Company):
            raise HTTPException(
                status_code=403,
                detail="Você não possui permissão para alterar essa assinatura."
            )

        elif plan.type == PlanType.individual and not isinstance(user, Client):
            raise HTTPException(
                status_code=403,
                detail="Você não possui permissão para alterar essa assinatura."
            )
        
        target_plan = plan
        
        # Alteração no banco
        if subscription_data.plan_id:
            new_plan = await session.get(SubscriptionPlan, subscription_data.plan_id)
            if not new_plan:
                raise HTTPException(
                    status_code=404,
                    detail="Novo plano não encontrado."
                )
            if new_plan.type != plan.type:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível alterar o tipo de plano."
                )
            subscription.plan_id = subscription_data.plan_id
            target_plan = new_plan

        if target_plan.type == PlanType.individual:
            subscription.max_managers_purchased = 0
            subscription.max_employees_purchased = 0

        else:
            if subscription_data.managers_quantity is not None:
                subscription.max_managers_purchased = subscription_data.managers_quantity

            if subscription_data.employees_quantity is not None:
                subscription.max_employees_purchased = subscription_data.employees_quantity

        sum_licenses = subscription.max_managers_purchased + subscription.max_employees_purchased
        final_license_quantity = max(1, sum_licenses)
        subscription.price_at_purchase = Decimal(target_plan.price_in_cents) * final_license_quantity / Decimal(100)
        subscription.license_quantity = final_license_quantity

        await session.flush()
        
        price = int(target_plan.price_in_cents)
        total_price = round((final_license_quantity * price) / 100, 2)
        mp_sub_id = subscription.mp_subscription_id

        mp_frequency_map = {
            PlanPeriod.monthly: 1,
            PlanPeriod.quarterly: 3,
            PlanPeriod.semiannual: 6,
            PlanPeriod.annual: 12,
        }

        mp_frequency = mp_frequency_map.get(target_plan.period, 1)

        # Atualização de preço no MP
        if mp_sub_id:
            subscription_update_data = {
            "auto_recurring": {
                "transaction_amount": total_price,
                "frequency": mp_frequency,
                "frequency_type": "months"
                },
            }
            try:
                result = await mp_call(sdk.preapproval().update, mp_sub_id, subscription_update_data)

                if result.get("status") not in [200, 201]:
                    mp_response = result.get("response", {}) if isinstance(result, dict) else {}
                    await session.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail={"message": "Erro do Mercado Pago ao criar assinatura", "mp_response": mp_response}
                    )
                
            except HTTPException:
                raise

            except Exception as e:
                await session.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao atualizar assinatura no Mercado Pago: {str(e)}"
                )
        
        await session.commit()
        await session.refresh(subscription)
        return subscription
    
    @staticmethod
    async def cancel_subscription(session: AsyncSession, subscription_id: int, user: Any, sdk: mercadopago.SDK): 

        if isinstance(user, Client):
            query = (
                select(Subscription)
                .where(Subscription.client_id == user.id)
                .order_by(Subscription.id.desc())
            )
        elif isinstance(user, Company):
            query = (
                select(Subscription)
                .where(Subscription.company_id == user.id)
                .order_by(Subscription.id.desc())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de usuário inválido."
            )

        result = await session.execute(query)
        subscription = result.scalars().first()

        if not subscription or subscription.id != subscription_id:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma assinatura foi encontrada."
            )
        
        if subscription.status == SubscriptionStatus.canceled:
            raise HTTPException(
                status_code=400,
                detail="Esta assinatura já está cancelada"
            )
        
        plan = await session.get(SubscriptionPlan, subscription.plan_id)
        if not plan:
            raise HTTPException(
                status_code=404,
                detail="Plano vinculado à assinatura não encontrado."
            )

        # Verifica o tipo de usuário para conceder as permissões
        if plan.type == PlanType.corporative and not isinstance(user, Company):
            raise HTTPException(
                status_code=403,
                detail="Você não possui permissão para excluir essa assinatura."
            )

        elif plan.type == PlanType.individual and not isinstance(user, Client):
            raise HTTPException(
                status_code=403,
                detail="Você não possui permissão para excluir essa assinatura."
            )
        
        # Inativação da assinatura no MP e Banco (alteração de status)
        if subscription.mp_subscription_id:
            try:
                mp_response = await mp_call(sdk.preapproval().update, subscription.mp_subscription_id, {"status": "cancelled"})  
                if mp_response.get("status") not in [200, 201]:
                    raise HTTPException(status_code=400, detail="Erro ao cancelar no Mercado Pago.")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao cancelar no Mercado Pago. Tente novamente. {str(e)}"
                )
        subscription.status = SubscriptionStatus.canceled
        subscription.end_date = datetime.now(timezone.utc) # Registra data e horário que a assinatura foi inativada

        await session.commit()