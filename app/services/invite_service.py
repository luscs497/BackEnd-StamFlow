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
from app.services.email_templates import build_invite_email_html

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
            await InviteService._reserve_licenses(session, cid, managers_to_add=1)

        elif request.role == InviteRole.employee:
            await InviteService._reserve_licenses(session, cid, employees_to_add=1)

        token = secrets.token_urlsafe(32)

        new_invite = Invite(
            email=request.email,
            role=request.role,
            token=token,
            company_id=cid,
            manager_id=manager_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
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
        html_body = build_invite_email_html(register_link, function_name)

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

        if managers_to_add > 0 and isinstance(user, Manager):
            raise HTTPException(
                status_code=403,
                detail="Apenas administradores da empresa podem convidar novos gestores."
            )
        
        employees_to_add = sum(1 for req in requests if req.role == InviteRole.employee)

        if managers_to_add > 0 or employees_to_add > 0:
            await InviteService._reserve_licenses(session, cid, employees_to_add=employees_to_add, managers_to_add=managers_to_add)

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
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
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
            
            html_body = build_invite_email_html(register_link, function_name)
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
        if managers_to_add > 0 or employees_to_add > 0:
            await InviteService._reserve_licenses(session, company_id, employees_to_add=employees_to_add, managers_to_add=managers_to_add)
            
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
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            invites_to_create.append(new_invite)

            html_body = build_invite_email_html(register_link, function_name, name=name)
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
    async def _reserve_licenses(session: AsyncSession, company_id: int, employees_to_add: int = 0, managers_to_add: int = 0) -> None:
        """
        Verifica e "reserva" vagas de licença de forma segura contra concorrência.

        Problema que isso resolve: can_add_employee/can_add_manager fazem um
        SELECT COUNT simples. Se duas requisições de convite chegarem quase
        juntas (duplo clique, dois gestores convidando ao mesmo tempo), as
        duas poderiam ler a mesma contagem "atual", ambas passarem a
        checagem, e juntas excederem o limite contratado — já que nenhuma
        delas via o efeito da outra ainda.

        SELECT ... FOR UPDATE trava a linha da Subscription até o fim da
        transação (commit/rollback do caller). Uma segunda requisição
        concorrente que tente o mesmo SELECT FOR UPDATE vai BLOQUEAR até a
        primeira terminar — só então lê a contagem já atualizada. Isso
        serializa as duas checagens, eliminando a janela de corrida.

        Não comita aqui de propósito: o lock só deve ser liberado quando o
        caller terminar de criar os Invites e comitar essa mesma transação.
        """
        stmt = select(Subscription).where(Subscription.company_id == company_id).with_for_update()
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or subscription.status != SubscriptionStatus.active.value:
            raise HTTPException(
                status_code=403,
                detail="Não há uma assinatura ativa para esta empresa."
            )

        if managers_to_add > 0:
            used_managers = await InviteService._count_managers_usage(session, company_id)
            if used_managers + managers_to_add > subscription.max_managers_purchased:
                raise HTTPException(
                    status_code=403,
                    detail=f"Limite de gestores atingido. Você tentou convidar {managers_to_add} gestor(es), mas não há vagas suficientes."
                )

        if employees_to_add > 0:
            used_employees = await InviteService._count_employees_usage(session, company_id)
            if used_employees + employees_to_add > subscription.max_employees_purchased:
                raise HTTPException(
                    status_code=403,
                    detail=f"Limite de funcionários atingido. Você tentou convidar {employees_to_add} funcionário(s), mas não há vagas suficientes."
                )

    @staticmethod
    async def _count_employees_usage(session: AsyncSession, company_id: int) -> int:
        """Clientes ativos da empresa + convites de funcionário ainda pendentes."""
        current_employees = await session.scalar(
            select(func.count(Client.id)).where(Client.company_id == company_id)
        ) or 0
        pending_invites = await session.scalar(
            select(func.count(Invite.id))
            .where(Invite.company_id == company_id)
            .where(Invite.role == InviteRole.employee)
            .where(Invite.status == InviteStatus.pending)
        ) or 0
        return current_employees + pending_invites

    @staticmethod
    async def _count_managers_usage(session: AsyncSession, company_id: int) -> int:
        """Gestores ativos da empresa + convites de gestor ainda pendentes."""
        current_managers = await session.scalar(
            select(func.count(Manager.id)).where(Manager.company_id == company_id)
        ) or 0
        pending_invites = await session.scalar(
            select(func.count(Invite.id))
            .where(Invite.company_id == company_id)
            .where(Invite.role == InviteRole.manager)
            .where(Invite.status == InviteStatus.pending)
        ) or 0
        return current_managers + pending_invites

    @staticmethod
    async def can_add_employee(session: AsyncSession, company: Company, quantity: int = 1) -> bool:

        stmt = select(Subscription).where(Subscription.company_id == company.id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or subscription.status != SubscriptionStatus.active.value:
            return False

        final_quantity = await InviteService._count_employees_usage(session, company.id) + quantity
        return final_quantity <= subscription.max_employees_purchased

    @staticmethod
    async def can_add_manager(session: AsyncSession, company: Company, quantity: int = 1) -> bool:

        stmt = select(Subscription).where(Subscription.company_id == company.id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or subscription.status != SubscriptionStatus.active.value:
            return False

        final_quantity = await InviteService._count_managers_usage(session, company.id) + quantity
        return final_quantity <= subscription.max_managers_purchased

    @staticmethod
    async def get_license_usage(session: AsyncSession, company_id: int) -> dict:
        """
        Retorna o uso atual de licença da empresa (quantos colaboradores/gestores
        já ocupam vaga vs. o limite contratado). Usado pela tela de Colaboradores
        para mostrar quantas vagas restam ANTES do gestor tentar convidar alguém,
        em vez de só descobrir o limite ao receber um 403 do backend.
        """
        stmt = select(Subscription).where(Subscription.company_id == company_id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        subscription_active = bool(subscription) and subscription.status == SubscriptionStatus.active.value

        used_employees = await InviteService._count_employees_usage(session, company_id)
        used_managers = await InviteService._count_managers_usage(session, company_id)

        return {
            "max_employees": subscription.max_employees_purchased if subscription else 0,
            "used_employees": used_employees,
            "max_managers": subscription.max_managers_purchased if subscription else 0,
            "used_managers": used_managers,
            "subscription_active": subscription_active,
        }

    @staticmethod
    async def get_invite_preview_by_token(session: AsyncSession, token: str) -> Invite:
        """
        Busca um convite PENDENTE e não expirado pelo token, sem exigir
        autenticação — usado pela página pública de criação de conta
        (registerEmployee.html) para mostrar o e-mail do convidado antes do
        cadastro, e para validar o link antes mesmo de o usuário preencher o
        formulário.
        """
        result = await session.execute(select(Invite).where(Invite.token == token))
        invite = result.scalar_one_or_none()

        if not invite:
            raise HTTPException(status_code=404, detail="Convite não encontrado.")

        if invite.status != InviteStatus.pending:
            raise HTTPException(status_code=400, detail="Esse convite já foi usado ou cancelado.")

        if invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Esse convite expirou.")

        return invite
