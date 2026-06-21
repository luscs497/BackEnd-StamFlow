from fastapi import APIRouter, Depends
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.account_service import AccountService

router = APIRouter()


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Perfil consolidado: conta + assinatura/licença + trial + links dos painéis."""
    return await AccountService.get_profile(session=db, user=user)
