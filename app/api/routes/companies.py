from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List, Union
from app.db.session import get_db
from app.api.deps import verify_admin_token, get_current_company
from app.services.company_service import CompanyService
from app.models.company import Company
from app.schemas.manager import ManagerResponse
from app.schemas.auth import ClientResponse
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate
)

router = APIRouter()

@router.post("/register", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin_token)])
async def register_company(company_data: CompanyCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    new_company = await CompanyService.register_company(db, company_data)
    return new_company

@router.get("/", response_model=CompanyResponse)
async def get_company(current_company: Annotated[Company, Depends(get_current_company)]):
    return current_company

@router.get("/all", response_model=List[CompanyResponse], dependencies=[Depends(verify_admin_token)])
async def get_companies(db: Annotated[AsyncSession, Depends(get_db)]):
    return await CompanyService.get_all_companies(db)

@router.patch("/update", response_model=CompanyResponse)
async def update_company(db: Annotated[AsyncSession, Depends(get_db)], data: CompanyUpdate, current_company: Company = Depends(get_current_company)):
    return await CompanyService.update_company(db, current_company, data)

@router.get("/team", response_model=List[Union[ClientResponse, ManagerResponse]])
async def get_team(db: Annotated[AsyncSession, Depends(get_db)], current_company: Company = Depends(get_current_company)):
    return await CompanyService.get_team(db, current_company)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_token)])
async def delete_company(db: Annotated[AsyncSession, Depends(get_db)], company_id: int):
    await CompanyService.delete_company(db, company_id)