from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import verify_admin_token
from app.models.enterprise_request import EnterpriseRequestStatus
from app.schemas.enterprise import (
    EnterpriseRequestCreate, EnterpriseRequestResponse,
    EnterpriseStatusUpdate, EnterpriseProvision,
)
from app.services.enterprise_service import EnterpriseService

router = APIRouter()


@router.post("/request")
async def create_request(data: EnterpriseRequestCreate, db: AsyncSession = Depends(get_db)):
    """Público: empresa solicita proposta. Registra no funil e devolve o link do WhatsApp."""
    return await EnterpriseService.create_request(session=db, data=data)


@router.get("/requests", response_model=List[EnterpriseRequestResponse],
            dependencies=[Depends(verify_admin_token)])
async def list_requests(
    status: Optional[EnterpriseRequestStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await EnterpriseService.list_requests(session=db, status=status)


@router.get("/requests/{request_id}", response_model=EnterpriseRequestResponse,
            dependencies=[Depends(verify_admin_token)])
async def get_request(request_id: int, db: AsyncSession = Depends(get_db)):
    return await EnterpriseService.get_request(session=db, request_id=request_id)


@router.patch("/requests/{request_id}/status", response_model=EnterpriseRequestResponse,
              dependencies=[Depends(verify_admin_token)])
async def update_status(
    request_id: int, body: EnterpriseStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await EnterpriseService.update_status(session=db, request_id=request_id, new_status=body.status)


@router.post("/requests/{request_id}/provision", dependencies=[Depends(verify_admin_token)])
async def provision(request_id: int, body: EnterpriseProvision, db: AsyncSession = Depends(get_db)):
    return await EnterpriseService.provision(session=db, request_id=request_id, data=body)
