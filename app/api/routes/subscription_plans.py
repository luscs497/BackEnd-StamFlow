from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from app.db.session import get_db
from app.api.deps import verify_admin_token
from app.services.subscription_plan_service import SubscriptionPlanService
from app.schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate

router = APIRouter()

@router.post("/register", response_model=SubscriptionPlanResponse, dependencies=[Depends(verify_admin_token)])
async def register_subscription_plan(subscription_plan_data: SubscriptionPlanCreate, db: AsyncSession = Depends(get_db)):
    new_subscription_plan = await SubscriptionPlanService.register_subscription_plan(db, subscription_plan_data)
    return new_subscription_plan

@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def read_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    return await SubscriptionPlanService.read_plans(db)

@router.get("/{plan_id}", response_model=SubscriptionPlanResponse)
async def read_subscription_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await SubscriptionPlanService.read_plan(db, plan_id)

@router.patch("/update/{plan_id}", response_model=SubscriptionPlanResponse, dependencies=[Depends(verify_admin_token)])
async def update_subscription_plan(plan_id: int, subscription_data: SubscriptionPlanUpdate, db: AsyncSession = Depends(get_db)):
    return await SubscriptionPlanService.update_subscription_plan(plan_id, subscription_data, db)

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_token)])
async def delete_subscription_plan(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):    
    return await SubscriptionPlanService.delete_subscription_plan(db, plan_id)