from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status
from typing import Optional, Any, List
import hashlib
from datetime import datetime, timezone, timedelta

from app.models.client import Client
from app.models.manager import Manager
from app.models.company import Company
from app.models.invite import Invite, InviteStatus, InviteRole
from app.models.client_token import ClientToken
from app.schemas.auth import ClientCreate
from app.services.utils import is_email_in_use, is_cpf_in_use

from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    decode_token
)
from app.core.config import settings

class AuthService:
    
    @staticmethod
    async def authenticate_user(session: AsyncSession, email: str, password: str):
        # 1. Tentar achar como Cliente
        result_client = await session.execute(select(Client).where(Client.email == email))
        client = result_client.scalar_one_or_none()

        if client:
            if verify_password(password, client.senha_hash):
                return client, "client"
        
        # 2. Tenta achar como Manager
        result_manager = await session.execute(select(Manager).where(Manager.email == email))
        manager = result_manager.scalar_one_or_none()

        if manager:
            if verify_password(password, manager.senha_hash):
                return manager, "manager"
            
        # 3. Tenta achar como Company
        result_company = await session.execute(select(Company).where(Company.email == email))
        company = result_company.scalar_one_or_none()

        if company:
            if verify_password(password, company.senha_hash):
                return company, "company"

        return None, None

    @staticmethod
    async def register_client(session: AsyncSession, data: ClientCreate) -> Client:
        if data.token:
            result = await session.execute(select(Invite).where(Invite.token == data.token))
            invite = result.scalar_one_or_none()
            if not invite:
                raise HTTPException(
                    status_code=404,
                    detail="Convite inválido ou não encontrado."
                )
            if invite.role != InviteRole.employee:
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
            final_email = invite.email
        else:
            # Verifica se o CPF já existe
            if await is_cpf_in_use(session, data.cpf):
                raise HTTPException(
                    status_code=400,
                    detail="Este CPF já está em uso."
                )
            if not data.email:
                raise HTTPException(
                    status_code=400,
                    detail="É necessário inserir um e-mail para o cadastro."
                )
            final_email = data.email

            # Verifica se email já existe (apenas no cadastro avulso).
            # No fluxo via convite, o próprio convite pendente faria o
            # is_email_in_use retornar True (falso positivo), bloqueando o
            # convidado de se registrar. O convite já garante a validade.
            if await is_email_in_use(session, final_email):
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já está cadastrado."
                )

        if data.token:
            new_client = Client(
                email=final_email,
                senha_hash=hash_password(data.senha), 
                company_id=invite.company_id,
                manager_id=invite.manager_id
            )
            invite.status = InviteStatus.accepted
            session.add(invite)
            session.add(new_client)

        else:
            new_client = Client(
                nome_completo=data.nome_completo,
                cpf=data.cpf,
                telefone=data.telefone,
                email=final_email,
                senha_hash=hash_password(data.senha)
            )
            session.add(new_client)

        try:
            await session.commit()
            await session.refresh(new_client)
            return new_client
        
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail="Já existe um usuário cadastrado com esse CPF ou e-mail."
            )    

    @staticmethod
    async def create_tokens_for_user(session: AsyncSession, user_id: int, user_type: str, company_id: Optional[int], manager_id: Optional[int] = None, user_agent: str = None, ip: str = None):
        access_token = create_access_token(
            user_id=user_id,
            user_type=user_type,
            company_id=company_id,
            manager_id=manager_id
        )
        
        refresh_token = create_refresh_token(
            user_id=user_id,
            user_type=user_type,
            company_id=company_id,
            manager_id=manager_id
        )

        # Salva o refresh token do cliente no banco para segurança
        if user_type == "client":
            rf_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            
            expire_date = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

            db_token = ClientToken(
                client_id=user_id,
                refresh_token_hash=rf_hash,
                user_agent=user_agent,
                ip_address=ip, # Agora o banco aceita string formatada como IP
                expira_em=expire_date,
                revogado=False
            )
            session.add(db_token)
            await session.commit()

        return access_token, refresh_token

    # --- NOVA FUNÇÃO DE REFRESH ---
    @staticmethod
    async def refresh_access_token(session: AsyncSession, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

        user_id = payload.get("sub")
        user_type = payload.get("user_type")
        company_id = payload.get("company_id")
        manager_id = payload.get("manager_id")

        if not user_id or not user_type:
             raise HTTPException(status_code=401, detail="Token malformado")

        # Se for cliente, temos uma camada extra de segurança: Verificar no banco
        if user_type == "client":
            rf_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            
            # Busca o token no banco que tenha esse hash E pertença a esse usuário
            stmt = select(ClientToken).where(
                and_(
                    ClientToken.refresh_token_hash == rf_hash,
                    ClientToken.client_id == int(user_id)
                )
            )
            result = await session.execute(stmt)
            db_token = result.scalar_one_or_none()

            # Verificações de segurança
            if not db_token:
                # Se o token existe criptograficamente mas não está no banco, algo estranho aconteceu
                raise HTTPException(status_code=401, detail="Token não encontrado na base (Login necessário)")
            
            if db_token.revogado:
                raise HTTPException(status_code=401, detail="Sessão revogada/inválida")
        
        # Se passou por tudo, gera um NOVO Access Token
        new_access_token = create_access_token(
            user_id=int(user_id),
            user_type=user_type,
            company_id=company_id,
            manager_id=manager_id
        )

        # Retornamos o Access Token novo e o Refresh Token antigo (que ainda é válido até expirar)
        return new_access_token, refresh_token
    
    @staticmethod
    async def delete_client(session: AsyncSession, current_user: Any, client_id: int):
        
        client = await session.get(Client, client_id)

        if not client:
            raise HTTPException(
                status_code=404,
                detail="O usuário não foi encontrado."
            )
        
        if isinstance(current_user, Company):
            if current_user.id != client.company_id:
                raise HTTPException(
                    status_code=403,
                    detail="O usuário não tem permissão para realizar essa operação."
                )
            
        elif isinstance(current_user, Manager):
            # Escopo compartilhado: qualquer gestor da empresa pode excluir
            # qualquer colaborador da mesma empresa (consistente com a
            # listagem da equipe, que também é por company_id).
            if current_user.company_id != client.company_id:
                raise HTTPException(
                    status_code=403,
                    detail="O usuário não tem permissão para realizar essa operação."
                )
        
        else:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não tem permissão para realizar essa operação."
            )
        await session.delete(client)
        await session.commit()

    @staticmethod
    async def delete_clients_bulk(session: AsyncSession, user: Any, client_ids: List[int]):
        if not client_ids:
            return 

        if isinstance(user, Client):
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não tem permissão para realizar essa operação."
            )
        
        try:
            query = delete(Client).where(Client.id.in_(client_ids))
            if isinstance(user, Company):
                query = query.where(Client.company_id == user.id)
            elif isinstance(user, Manager):
                # Mesmo raciocínio do delete individual: escopo por empresa,
                # não por manager_id, para ficar consistente com a listagem.
                query = query.where(Client.company_id == user.company_id)
            result = await session.execute(query)
            await session.commit()
            
            # Verificar quantos foram deletados
            deleted_qty = result.rowcount #type: ignore
            if deleted_qty == 0:
               raise HTTPException(404, "Nenhum colaborador válido encontrado para exclusão.")
            elif deleted_qty != len(client_ids):
                raise HTTPException(401, "Não foi possível realizar exclusão completamente. Há alguns colaboradores que você não tem propriedade.")
                
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Erro interno ao tentar deletar colaboradores.")