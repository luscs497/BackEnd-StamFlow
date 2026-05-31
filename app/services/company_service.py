from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from typing import List
from fastapi import HTTPException

from app.models.client import Client
from app.models.manager import Manager
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.utils import is_email_in_use

from app.core.security import hash_password

class CompanyService:
    @staticmethod
    async def register_company(session: AsyncSession, data: CompanyCreate) -> Company:  

        # Verifica se email já existe
        if await is_email_in_use(session, data.email):
            raise HTTPException(
                status_code=400,
                detail="Este e-mail já está cadastrado."
            )
        
        # Verifica se o CNPJ já existe
        stmt = select(Company).where(Company.cnpj == data.cnpj)
        result = await session.execute(stmt)
        existing_cnpj = result.scalar_one_or_none()

        if existing_cnpj:
            raise HTTPException(
                status_code=400,
                detail="Este CNPJ já está cadastrado."
            )

        new_company = Company(
            nome_fantasia=data.nome_fantasia,
            razao_social=data.razao_social,
            email=data.email,
            cnpj=data.cnpj,
            telefone=data.telefone,
            senha_hash=hash_password(data.senha)
        )

        try:
            session.add(new_company)
            await session.commit()
            await session.refresh(new_company)
            return new_company
        
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail="Já existe uma empresa cadastrada com esse CNPJ ou e-mail."
            )    
        
    @staticmethod
    async def get_all_companies(session: AsyncSession) -> List[Company]:
        stmt = select(Company).options(selectinload(Company.subscription))
        result = await session.execute(stmt)
        companies = list(result.scalars().all())
        return companies
    
    @staticmethod
    async def update_company(session: AsyncSession, current_company: Company, data: CompanyUpdate) -> Company:

        if data.email and data.email != current_company.email:
            if await is_email_in_use(session, data.email):
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já está cadastrado."
                )
            
        if data.cnpj and data.cnpj != current_company.cnpj:    
            stmt = select(Company).where(Company.cnpj == data.cnpj)
            result = await session.execute(stmt)
            existing_cnpj = result.scalar_one_or_none()

            if existing_cnpj:
                raise HTTPException(
                    status_code=400,
                    detail="Este CNPJ já está cadastrado."
                )
        
            
        update_data = data.model_dump(exclude_unset=True)
        if "senha" in update_data:
            senha_plana = update_data.pop("senha")
            update_data["senha_hash"] = hash_password(senha_plana)
            
        for key, value in update_data.items():
            setattr(current_company, key, value)
        
        try:
            await session.commit()
            await session.refresh(current_company)
            await session.execute(
                select(Company)
                .options(selectinload(Company.subscription))
                .where(Company.id == current_company.id)
            )
            return current_company
        
        except IntegrityError:
            raise HTTPException(
                status_code=400,
                detail="Já existe uma empresa cadastrada com esse CNPJ ou e-mail."
            )
    
    @staticmethod
    async def delete_company(session, company_id):
        company = await session.get(Company, company_id)

        if not company:
            raise HTTPException(
                status_code=404,
                detail="A empresa não foi encontrada."
            )
        
        await session.delete(company)
        await session.commit()

    @staticmethod
    async def get_team(session: AsyncSession, company: Company):
        cid = company.id            
        try:
            clients_result = await session.execute(select(Client).where(Client.company_id == cid))
            clients = clients_result.scalars().all()
            managers_result = await session.execute(select(Manager).where(Manager.company_id == cid))
            managers = managers_result.scalars().all()

            return [*managers, *clients]

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível buscar o time da empresa."
            )