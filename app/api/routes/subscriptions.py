from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Annotated
from app.db.session import get_db
from app.api.deps import get_current_user, get_mp_sdk
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionResponse, SubscriptionCheckoutRequest, SubscriptionUpdate
import mercadopago

router = APIRouter()

@router.post("/checkout/subscribe")
async def process_checkout(data: SubscriptionCheckoutRequest, db: AsyncSession = Depends(get_db), user: Any = Depends(get_current_user), sdk: mercadopago.SDK = Depends(get_mp_sdk)):
    return await SubscriptionService.process_checkout(session=db, data=data, user=user, sdk=sdk)

@router.get("/my-subscription", response_model=SubscriptionResponse)
async def read_subscription(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Any = Depends(get_current_user)
):
    return await SubscriptionService.read_subscription(db, current_user)

@router.patch("/update", response_model=SubscriptionResponse)
async def update_subscription(subscription_data: SubscriptionUpdate, current_user: Any = Depends(get_current_user), db: AsyncSession = Depends(get_db), sdk: mercadopago.SDK = Depends(get_mp_sdk)):
    return await SubscriptionService.update_subscription(db, subscription_data, current_user, sdk=sdk)
    
@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sdk: mercadopago.SDK = Depends(get_mp_sdk)
):    
    await SubscriptionService.cancel_subscription(db, subscription_id, current_user, sdk=sdk)