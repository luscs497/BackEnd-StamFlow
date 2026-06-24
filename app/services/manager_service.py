from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.manager import Manager
from app.models.client import Client
from app.models.company import Company
from app.models.invite import Invite, InviteStatus, InviteRole
from app.schemas.manager import ManagerCreate, ManagerUpdate
from app.services.utils import is_email_in_use, is_cpf_in_use

from app.core.security import hash_password
from datetime import datetime, timezone

class ManagerService:
    @staticmethod
    async def register_manager(session: AsyncSession, data: ManagerCreate) -> Manager:
        result = await session.execute(select(Invite).where(Invite.token == data.token))
        invite = result.scalar_one_or_none()

        if not invite:
            raise HTTPException(
                status_code=404,
                detail="Convite inválido ou não encontrado."
            )
        
        if invite.role != InviteRole.manager:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não tem permissão para realizar essa operação."
            )
        
        if invite.status != InviteStatus.pending:
            raise HTTPException(
                status_code=400,
                detail="Esse convite já foi usado ou cancelado."
            )
        
        if invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="Esse convite expirou."
            )
        
        # Verifica se email já existe
        if await is_email_in_use(session, invite.email):
            raise HTTPException(
                status_code=400,
                detail="Este e-mail já está cadastrado."
            )
        
        # Verifica se o CPF já existe
        if await is_cpf_in_use(session, data.cpf):
            raise HTTPException(
                status_code=400,
                detail="Este CPF já está em uso."
            )
        
        new_manager = Manager(
            nome=data.nome,
            cpf=data.cpf,
            telefone=data.telefone,
            email=invite.email,
            senha_hash=hash_password(data.senha), 
            company_id=invite.company_id
        )
        try:
            invite.status = InviteStatus.accepted
            session.add(invite)
            session.add(new_manager)
            await session.commit()
            await session.refresh(new_manager)
            return new_manager
        
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail="Já existe um usuário cadastrado com esse CPF ou e-mail."
            )
    
    @staticmethod
    async def update_manager(session: AsyncSession, manager: Manager, data: ManagerUpdate):
        
        # Transforma os dados em um dicionário que pode conter algum campo vazio
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return manager
        
        if data.email and data.email != manager.email:
            if await is_email_in_use(session, data.email):
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já está cadastrado."
                )
        
        if data.cpf and data.cpf != manager.cpf:
            # Verifica se o CPF já existe
            if await is_cpf_in_use(session, data.cpf):
                raise HTTPException(
                    status_code=400,
                    detail="Este CPF já está em uso."
                )

        if "senha" in update_data:
            senha_plana = update_data.pop("senha") 
            update_data["senha_hash"] = hash_password(senha_plana)
            
        try:
            for field, value in update_data.items():
                if hasattr(manager, field):
                    setattr(manager, field, value)

            await session.commit()
            await session.refresh(manager)
            return manager

        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail="Este e-mail já está em uso por outro usuário."
            )

        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao atualizar os dados."
            )        
    
    @staticmethod
    async def delete_manager(session: AsyncSession, current_company: Company, manager_id: int):

        manager = await session.get(Manager, manager_id)

        if not manager:
            raise HTTPException(
                status_code=404,
                detail="O gestor não foi encontrado."
            )
        
        if current_company.id != manager.company_id:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não tem permissão para realizar essa operação."
            )
        
        await session.delete(manager)
        await session.commit()

    @staticmethod
    async def get_team(session: AsyncSession, manager: Manager):
        try:
            # Visão compartilhada: todos os colaboradores da EMPRESA, não só os
            # que este gestor específico convidou (Client.manager_id). Antes,
            # filtrar por manager_id escondia colaboradores convidados pela
            # Company diretamente ou por outro gestor da mesma empresa.
            result = await session.execute(select(Client).where(Client.company_id == manager.company_id))
            team = result.scalars().all()
            return list(team)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível buscar o time do(a) gestor(a)."
            )

    @staticmethod
    async def get_team_with_status(session: AsyncSession, manager: Manager):
        """
        Visão unificada de colaboradores: mescla Clients já registrados
        (status "ativo" — a única forma de existir um Client com company_id
        preenchido é ter concluído o cadastro via convite) com Invites de
        funcionário ainda pendentes (status "inativo" — convite enviado, mas
        o destinatário não concluiu a criação da conta).

        Não usamos os Invites com status "accepted" aqui: o Client correspondente
        já cobre esse caso, e listar os dois lados duplicaria a mesma pessoa.
        """
        try:
            company_id = manager.company_id

            clients_result = await session.execute(
                select(Client).where(Client.company_id == company_id)
            )
            clients = clients_result.scalars().all()

            invites_result = await session.execute(
                select(Invite).where(
                    Invite.company_id == company_id,
                    Invite.role == InviteRole.employee,
                    Invite.status == InviteStatus.pending,
                )
            )
            pending_invites = invites_result.scalars().all()

            team = [
                {
                    "origin": "client",
                    "origin_id": c.id,
                    "email": c.email,
                    "nome_completo": c.nome_completo,
                    "status": "ativo",
                    "criado_em": c.criado_em,
                }
                for c in clients
            ] + [
                {
                    "origin": "invite",
                    "origin_id": i.id,
                    "email": i.email,
                    "nome_completo": None,
                    "status": "inativo",
                    "criado_em": i.created_at,
                }
                for i in pending_invites
            ]

            return team

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível buscar o time do(a) gestor(a)."
            )