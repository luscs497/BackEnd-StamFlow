from typing import Literal, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.subscription_plan import PlanType
from app.models.subscription import SubscriptionStatus
from app.schemas.subscription_plan import SubscriptionPlanResponse
from app.schemas.auth import ClientResponse
from app.schemas.manager import ManagerResponse
from app.schemas.company import CompanyResponse

class SubscriptionCheckoutRequest(BaseModel):
    plan_id: int
    managers_quantity: int = Field(default=0, ge=0)
    employees_quantity: int = Field(default=0, ge=0)

class SubscriptionResponse(BaseModel):
    id: int
    plan: SubscriptionPlanResponse
    status: SubscriptionStatus
    initial_date: datetime
    end_date: Optional[datetime] = None
    license_quantity: int
    client: Optional[ClientResponse] = None
    company: Optional[CompanyResponse] = None
    mp_subscription_id: Optional[str] = None
    price_at_purchase: Decimal
    model_config = {"from_attributes": True}

class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    managers_quantity: Optional[int] = None
    employees_quantity: Optional[int] = None