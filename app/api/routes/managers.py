from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from app.db.session import get_db
from app.services.manager_service import ManagerService
from app.models.manager import Manager
from app.models.company import Company
from app.schemas.auth import ClientResponse
from app.schemas.manager import (
    ManagerCreate,
    ManagerResponse,
    ManagerUpdate
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

@router.delete("/{manager_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manager(db: Annotated[AsyncSession, Depends(get_db)], current_company: Annotated[Company, Depends(get_current_company)], manager_id: int):
    await ManagerService.delete_manager(db, current_company, manager_id)