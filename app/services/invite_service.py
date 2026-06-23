from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Any
from fastapi import HTTPException, status

from app.models.company import Company
from app.models.manager import Manager
from app.models.client import Client
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invite import Invite, InviteRole, InviteStatus
from app.schemas.invite import InviteCreate
from app.services.utils import is_email_in_use, is_cpf_in_use

from app.core.config import settings, mail_conf
from fastapi import BackgroundTasks, UploadFile, File
import csv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import secrets
from datetime import datetime, timezone, timedelta

class InviteService:
    @staticmethod
    async def send_invite(
        session: AsyncSession,
        request: InviteCreate,
        user: Any,
        background_tasks: BackgroundTasks) -> dict:     
        if isinstance(user, Company):
            cid = user.id
            manager_id = None
        elif isinstance(user, Manager):
            cid = user.company_id
            manager_id = user.id
        else:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não possui autorização para realizar esta operação."
            )
        
        result = await session.execute(select(Company).where(Company.id == cid))
        existing_company = result.scalar_one_or_none()

        query = (
            select(Invite)
            .where(Invite.email == request.email)
            .where(Invite.company_id == cid)
            .where(Invite.status == InviteStatus.pending) 
            .where(Invite.expires_at > datetime.now(timezone.utc)) 
        )
        result = await session.execute(query)
        existing_invite = result.scalar_one_or_none()
        if not existing_company:
            raise HTTPException(
                status_code=400,
                detail="A empresa informada não existe."
            )

        if existing_invite:
            raise HTTPException(
                status_code=400,
                detail="Já existe um convite ativo e pendente para este e-mail."
            )
        
        if request.role == InviteRole.manager:
            if isinstance(user, Manager):
                raise HTTPException(
                    status_code=403,
                    detail="Apenas administradores da empresa podem convidar novos gestores."
                )
            if not await InviteService.can_add_manager(session, existing_company):
                raise HTTPException(
                    status_code=403,
                    detail="Limite de gestores atingido para seu plano atual."
                )
            
        elif request.role == InviteRole.employee:
            if not await InviteService.can_add_employee(session, existing_company):
                raise HTTPException(
                    status_code=403,
                    detail="Limite de funcionários atingido para seu plano atual."
                )

        token = secrets.token_urlsafe(32)

        new_invite = Invite(
            email=request.email,
            role=request.role,
            token=token,
            company_id=cid,
            manager_id=manager_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        session.add(new_invite)
        await session.commit()

        base_url = settings.BASE_URL 
        if request.role == InviteRole.manager:
            register_link = f"{base_url}/registerManager.html?token={token}"
            function_name = "Gestor(a)"
        else:
            register_link = f"{base_url}/registerEmployee.html?token={token}"
            function_name = "Colaborador(a)"
        
        # 4. Envia Email
        html_body = f"""
        <div style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #34D399;">Convite para o StamFlow</h2>
            <p>Olá,</p>
            <p>Você foi convidado(a) para se juntar ao sistema StamFlow como <strong>{function_name}</strong></p>
            <p>Clique no botão abaixo para criar sua conta e acessar a plataforma:</p>
            <a href="{register_link}" style="background-color: #34D399; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">Aceitar Convite</a>
            <p>Ou copie e cole este link no navegador:</p>
            <p>{register_link}</p>
            <p style="font-size: 12px; color: #777;">Este link expira em 7 dias.</p>
        </div>
        """

        message = MessageSchema(
            subject=f"Convite para ser {function_name} no StamFlow",
            recipients=[request.email],
            body=html_body,
            subtype=MessageType.html
        )

        fm = FastMail(mail_conf)
        background_tasks.add_task(fm.send_message, message)

        return {"message": f"Convite para {function_name} enviado com sucesso para o e-mail {request.email}."}
    
    @staticmethod
    async def get_invite(session: AsyncSession, user: Any, invite_id: int) -> Invite:
        if isinstance(user, Company):
            result = await session.execute(select(Invite).where(Invite.id == invite_id).where(Invite.company_id == user.id))
            invite = result.scalar_one_or_none()

        elif isinstance(user, Manager):
            result = await session.execute(select(Invite).where(Invite.id == invite_id).where(Invite.company_id == user.company_id))
            invite = result.scalar_one_or_none()

        if not invite:
            raise HTTPException(
                status_code=404,
                detail="O convite não foi encontrado."
            )
        return invite
    
    @staticmethod
    async def delete_invite(session: AsyncSession, user: Any, invite_id: int):
        invite = await session.get(Invite, invite_id)
        if not invite:
            raise HTTPException(
                status_code=404,
                detail="O convite não foi encontrado."
            )
        if isinstance(user, Company):
            if user.id != invite.company_id:
                raise HTTPException(
                    status_code=403,
                    detail="Você não possui permissão para excluir esse convite."
                )
        elif isinstance(user, Manager):
            if user.company_id != invite.company_id:
                raise HTTPException(
                    status_code=403,
                    detail="Você não possui permissão para excluir esse convite."
                )

        
        await session.delete(invite)
        await session.commit()

    @staticmethod
    async def get_all_invites(session: AsyncSession, user: Any):            
        try:
            if isinstance(user, Company):
                result = await session.execute(select(Invite).where(Invite.company_id == user.id))
                invites = result.scalars().all()
                return list(invites)
            
            elif isinstance(user, Manager):
                # Escopo compartilhado: todos os convites da empresa, não só
                # os que este gestor especificamente enviou — mesmo
                # raciocínio aplicado em ManagerService.get_team.
                result = await session.execute(select(Invite).where(Invite.company_id == user.company_id))
                invites = result.scalars().all()
                return list(invites)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível buscar os convites da empresa/gestor."
            )
        
    @staticmethod
    async def send_invites_bulk(
        session: AsyncSession,
        requests: List[InviteCreate],
        user: Any,
        background_tasks: BackgroundTasks
    ) -> dict:
        if isinstance(user, Company):
            cid = user.id
            manager_id = None
        elif isinstance(user, Manager):
            cid = user.company_id
            manager_id = user.id
        else:
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não possui autorização para realizar esta operação."
            )
            
        result = await session.execute(select(Company).where(Company.id == cid))
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=400, detail="Empresa não encontrada.")
        
        managers_to_add = sum(1 for req in requests if req.role == InviteRole.manager)

        if isinstance(user, Manager):
            raise HTTPException(
                status_code=403,
                detail="Apenas administradores da empresa podem convidar novos gestores."
            )
        
        employees_to_add = sum(1 for req in requests if req.role == InviteRole.employee)

        if managers_to_add > 0:
            if not await InviteService.can_add_manager(session, company, managers_to_add):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Limite de gestores atingido. Você tentou convidar {managers_to_add} gestores, mas não há vagas suficientes."
                )

        if employees_to_add > 0:
            if not await InviteService.can_add_employee(session, company, employees_to_add):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Limite de funcionários atingido. Você tentou convidar {employees_to_add} funcionários, mas não há vagas suficientes."
                )

        invites_to_create = []
        messages_to_send = []
        
        base_url = settings.BASE_URL 

        for req in requests:

            # Verifica se email já existe
            if await is_email_in_use(session, req.email):
                await session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já está cadastrado."
                )
            token = secrets.token_urlsafe(32)
            
            new_invite = Invite(
                email=req.email,
                role=req.role,
                status=InviteStatus.pending,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                token=token,
                company_id=cid,
                manager_id=manager_id
            )
            invites_to_create.append(new_invite)
            
            if req.role == InviteRole.manager:
                register_link = f"{base_url}/registerManager.html?token={token}"
                function_name = "Gestor(a)"
            else:
                register_link = f"{base_url}/registerEmployee.html?token={token}"
                function_name = "Funcionário(a)"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #34D399;">Convite para o StamFlow</h2>
                <p>Olá,</p>
                <p>Você foi convidado(a) para se juntar ao sistema StamFlow como <strong>{function_name}</strong></p>
                <p>Clique no botão abaixo para criar sua conta e acessar a plataforma:</p>
                <a href="{register_link}" style="background-color: #34D399; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">Aceitar Convite</a>
                <p>Ou copie e cole este link no navegador:</p>
                <p>{register_link}</p>
                <p style="font-size: 12px; color: #777;">Este link expira em 7 dias.</p>
            </div>
            """
            message = MessageSchema(
                subject=f"Convite para ser {function_name} no StamFlow",
                recipients=[req.email],
                body=html_body,
                subtype=MessageType.html
            )
            messages_to_send.append(message) 

        try:
            session.add_all(invites_to_create)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Um ou mais e-mails já possuem convite ou são inválidos.")

        fm = FastMail(mail_conf)
        for msg in messages_to_send:
            background_tasks.add_task(fm.send_message, msg) 

        return {
            "message": f"{len(invites_to_create)} convites gerados com sucesso e estão sendo enviados."
        }

    @staticmethod
    async def delete_invites_bulk(session: AsyncSession, user: Any, invite_ids: List[int]):
        if not invite_ids:
            return 
        
        if isinstance(user, Client):
            raise HTTPException(
                status_code=403,
                detail="O tipo de usuário não tem permissão para realizar essa operação."
            )
        
        try:
            query = delete(Invite).where(Invite.id.in_(invite_ids))
            if isinstance(user, Company):
                query = query.where(Invite.company_id == user.id)
            elif isinstance(user, Manager):
                query = query.where(Invite.company_id == user.company_id)
            result = await session.execute(query)
            await session.commit()
            
            # Verificar quantos foram deletados
            deleted_qty = result.rowcount #type: ignore
            if deleted_qty == 0:
               raise HTTPException(404, "Nenhum convite válido encontrado para exclusão.")
                
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Erro interno ao tentar deletar convites.")
        
    @staticmethod
    async def invite_csv(session: AsyncSession, user: Any, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Apenas arquivos CSV são aceitos."
            )
        contents = await file.read()
        try:
            csv_data = contents.decode('utf-8-sig').splitlines()
        except UnicodeDecodeError:
            try:
                csv_data = contents.decode('latin-1').splitlines()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="A codificação do arquivo não é suportada. Salve o arquivo como CSV (UTF-8) e tente novamente."
                )
        csv_reader = csv.reader(csv_data)
        next(csv_reader, None) # Pula o cabeçalho
        valid_rows = [row for row in csv_reader if row]
        
        if not valid_rows:
            raise HTTPException(status_code=400, detail="O arquivo CSV está vazio ou inválido.")
        
        if isinstance(user, Company):
            if any(len(row) < 3 for row in valid_rows):
                raise HTTPException(
                    status_code=400,
                    detail="O CSV da empresa deve conter 3 colunas: Nome, E-mail e Cargo."
                )
            managers_to_add = sum(1 for row in valid_rows if row[2].strip() in ["Gestor", "Gestora"])
            employees_to_add = len(valid_rows) - managers_to_add
            company_id = user.id
            manager_id = None

        elif isinstance(user, Manager):
            if any(len(row) < 2 for row in valid_rows):
                raise HTTPException(
                    status_code=400,
                    detail="O CSV do gestor deve conter 2 colunas: Nome e E-mail."
                )
            managers_to_add = 0
            employees_to_add = len(valid_rows)
            company_id = user.company_id
            manager_id = user.id

        else:
            raise HTTPException(
                status_code=403,
                detail="Apenas empresas e gestores podem realizar esta operação."
            )
        
        result = await session.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if managers_to_add > 0:
            if not await InviteService.can_add_manager(session, company, managers_to_add):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Limite atingido. O CSV contém {managers_to_add} gestores, mas você não tem vagas suficientes."
                )

        if employees_to_add > 0:
            if not await InviteService.can_add_employee(session, company, employees_to_add):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Limite atingido. O CSV contém {employees_to_add} funcionários, mas você não tem vagas suficientes."
                )
            
        invites_to_create = []
        messages_to_send = []
        base_url = settings.BASE_URL
        
        # Formato CSV para empresa -> Nome do convidado | E-mail | Cargo (Colaborador/Colaboradora/Gestor/Gestora)
        # Formato CSV para gestor -> Nome do convidado | E-mail
        for row in valid_rows:
            token = secrets.token_urlsafe(32)
            name = row[0].strip()
            email = row[1].strip()

            cargo = row[2].strip() if isinstance(user, Company) else "Colaborador(a)"

            if cargo in ["Gestor", "Gestora"]:
                role = InviteRole.manager
                function_name = "Gestor(a)"
                register_link = f"{base_url}/registerManager.html?token={token}"

            else:
                role = InviteRole.employee
                function_name = "Colaborador(a)"
                register_link = f"{base_url}/registerEmployee.html?token={token}"

            # Verifica se email já existe
            if await is_email_in_use(session, email):
                await session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já está cadastrado."
                )

            new_invite = Invite(
                email=email,
                role=role,
                token=token,
                company_id=company_id,
                manager_id=manager_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            invites_to_create.append(new_invite)

            html_body = f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #34D399;">Convite para o StamFlow</h2>
                <p>Olá, {name}</p>
                <p>Você foi convidado(a) para se juntar ao sistema StamFlow como <strong>{function_name}</strong></p>
                <p>Clique no botão abaixo para criar sua conta e acessar a plataforma:</p>
                <a href="{register_link}" style="background-color: #34D399; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">Aceitar Convite</a>
                <p>Ou copie e cole este link no navegador:</p>
                <p>{register_link}</p>
                <p style="font-size: 12px; color: #777;">Este link expira em 7 dias.</p>
            </div>
            """
            message = MessageSchema(
                subject=f"Convite para ser {function_name} no StamFlow",
                recipients=[email],
                body=html_body,
                subtype=MessageType.html
            )
            messages_to_send.append(message) 
        try:    
            session.add_all(invites_to_create)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail="Um ou mais e-mails já possuem convites ou são inválidos."
            )
        fm = FastMail(mail_conf)
        for msg in messages_to_send:
            background_tasks.add_task(fm.send_message, msg)
        return {"message": "Arquivo CSV enviado."}

    @staticmethod
    async def can_add_employee(session: AsyncSession, company: Company, quantity: int = 1) -> bool:

        stmt = select(Subscription).where(Subscription.company_id == company.id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or subscription.status != SubscriptionStatus.active.value:
            return False
        
        current_employees = await session.scalar(select(func.count(Client.id)).where(Client.company_id == company.id)) or 0
        pending_invites = await session.scalar(
            select(func.count(Invite.id))
            .where(Invite.company_id == company.id)
            .where(Invite.role == InviteRole.employee)
            .where(Invite.status == InviteStatus.pending)
        ) or 0

        final_quantity = current_employees + pending_invites + quantity
        return final_quantity <= subscription.max_employees_purchased

    @staticmethod
    async def can_add_manager(session: AsyncSession, company: Company, quantity: int = 1) -> bool:

        stmt = select(Subscription).where(Subscription.company_id == company.id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or subscription.status != SubscriptionStatus.active.value:
            return False
        
        current_managers = await session.scalar(select(func.count(Manager.id)).where(Manager.company_id == company.id)) or 0
        pending_invites = await session.scalar(
            select(func.count(Invite.id))
            .where(Invite.company_id == company.id)
            .where(Invite.role == InviteRole.manager)
            .where(Invite.status == InviteStatus.pending)
        ) or 0

        final_quantity = current_managers + pending_invites + quantity
        return final_quantity <= subscription.max_managers_purchased
        
