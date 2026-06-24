from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from app.db.session import get_db
from app.services.manager_service import ManagerService
from app.services.invite_service import InviteService
from app.models.manager import Manager
from app.models.company import Company
from app.schemas.auth import ClientResponse, TeamMemberResponse
from app.schemas.manager import (
    ManagerCreate,
    ManagerResponse,
    ManagerUpdate,
    LicenseUsageResponse
)
from app.api.deps import get_current_manager, get_current_company
router = APIRouter()

@router.post("/register", response_model=ManagerResponse, status_code=status.HTTP_201_CREATED)
async def register_manager(manager_data: ManagerCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    new_manager = await ManagerService.register_manager(db, manager_data)
    return new_manager

@router.get("/", response_model=ManagerResponse)
async def get_manager(current_manager: Annotated[Manager, Depends(get_current_manager)]):
    return current_manager

@router.patch("/update", response_model=ManagerResponse)
async def update_manager(db: Annotated[AsyncSession, Depends(get_db)], current_manager: Annotated[Manager, Depends(get_current_manager)], data: ManagerUpdate):
    return await ManagerService.update_manager(db, current_manager, data)

@router.get("/team", response_model=List[ClientResponse])
async def get_team(db: Annotated[AsyncSession, Depends(get_db)], current_manager: Annotated[Manager, Depends(get_current_manager)]): #=Depends(get_current_company)
    return await ManagerService.get_team(db, current_manager)

@router.get("/team/full", response_model=List[TeamMemberResponse])
async def get_team_full(db: Annotated[AsyncSession, Depends(get_db)], current_manager: Annotated[Manager, Depends(get_current_manager)]):
    """
    Visão unificada de colaboradores para a tela de Gestão de Acessos:
    Clients já registrados (status "ativo") + Invites de funcionário ainda
    pendentes (status "inativo"). Mantém /team intacto para não quebrar
    quem já depende do formato antigo.
    """
    return await ManagerService.get_team_with_status(db, current_manager)

@router.get("/license-usage", response_model=LicenseUsageResponse)
async def get_license_usage(db: Annotated[AsyncSession, Depends(get_db)], current_manager: Annotated[Manager, Depends(get_current_manager)]):
    """
    Uso atual de licença da empresa (quantas vagas de funcionário/gestor já
    estão ocupadas vs. o limite contratado). A tela de Colaboradores usa isso
    para avisar o gestor ANTES de ele tentar convidar alguém acima do limite,
    em vez de só descobrir isso ao receber um erro do backend.
    """
    return await InviteService.get_license_usage(db, current_manager.company_id)

@router.delete("/{manager_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manager(db: Annotated[AsyncSession, Depends(get_db)], current_company: Annotated[Company, Depends(get_current_company)], manager_id: int):
    await ManagerService.delete_manager(db, current_company, manager_id)