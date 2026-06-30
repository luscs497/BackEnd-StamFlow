from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.demo import DemoSignupRequest
from app.services.demo_service import DemoService
from app.core.limiter import limiter

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def signup_demo(
    request: Request,
    data: DemoSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Cadastro público da versão DEMO de 7 dias (limitada, sem cartão).
    Mesmo rate limit de /auth/register: contra spam de contas.
    """
    return await DemoService.signup_demo(db, data)
