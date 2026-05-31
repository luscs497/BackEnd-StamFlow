import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.company import Company
from app.models.manager import Manager
from app.models.invite import Invite, InviteStatus


# IMPORTANTE: uma AsyncSession do SQLAlchemy NÃO é segura para uso concorrente.
# Disparar várias queries em paralelo na mesma sessão (via asyncio.gather)
# causa IllegalStateChangeError / corrupção de conexão. Por isso as checagens
# abaixo são feitas SEQUENCIALMENTE, com retorno antecipado no primeiro match.

async def is_email_in_use(session: AsyncSession, email: str) -> bool:
    queries = (
        select(Client.id).where(Client.email == email).limit(1),
        select(Manager.id).where(Manager.email == email).limit(1),
        select(Company.id).where(Company.email == email).limit(1),
        select(Invite.id).where(
            Invite.email == email, Invite.status == InviteStatus.pending
        ).limit(1),
    )
    for query in queries:
        if await session.scalar(query) is not None:
            return True
    return False


async def is_cpf_in_use(session: AsyncSession, cpf: str) -> bool:
    queries = (
        select(Client.id).where(Client.cpf == cpf).limit(1),
        select(Manager.id).where(Manager.cpf == cpf).limit(1),
    )
    for query in queries:
        if await session.scalar(query) is not None:
            return True
    return False

async def mp_call(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)