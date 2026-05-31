from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.subscription_plan import PlanType, PlanPeriod

class SubscriptionPlanCreate(BaseModel):
    name: str
    price_in_cents: int
    description: str
    type: PlanType
    period: PlanPeriod

class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    price_in_cents: int
    description: str
    type: PlanType
    period: PlanPeriod
    is_active: bool
    model_config = {"from_attributes": True}

class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_in_cents: Optional[int] = None
    type: Optional[PlanType] = None
    period: Optional[PlanPeriod] = None
    is_active: Optional[bool] = None
    model_config = {"from_attributes": True}