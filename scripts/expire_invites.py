"""
Job de expiração de convites pendentes do StamFlow.

Remove da base os convites de funcionário/gestor que passaram do prazo
(expires_at < agora) sem serem aceitos (status ainda "pending"), e avisa por
e-mail quem enviou o convite — o gestor que convidou (Invite.manager_id) ou,
se foi a própria empresa que convidou direto (manager_id nulo), a empresa.

Por que remover em vez de só marcar como "expired": a tela de Colaboradores
(GET /manager/team/full) já trata todo Invite "pending" do tipo employee como
um colaborador "Inativo" na lista — não existe um terceiro estado visual para
"expirado". Deixar o registro pendente para sempre faria esses convites
acumularem na lista indefinidamente. Removê-lo é o que de fato "tira da lista
de colaboradores", como pedido.

Rodar manual (mesmo padrão de scripts/expire_subscriptions.py):
    cd /opt/apps/stamflow-api && .venv/bin/python scripts/expire_invites.py
Idempotente: se nada venceu, não altera nada e não envia e-mails.

Sugestão de agendamento (crontab -e), de hora em hora:
    0 * * * * cd /opt/apps/stamflow-api && .venv/bin/python scripts/expire_invites.py >> /var/log/stamflow/expire_invites.log 2>&1
"""
import os
import sys
import asyncio
from datetime import datetime, timezone

# raiz do projeto no path (permite "import app.*" rodando de qualquer lugar)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# importa todos os models para resolver as relationships entre eles
# CORREÇÃO I2: faltava 'notification' (mesmo motivo do expire_subscriptions —
# Client.notifications = relationship("Notification") quebra o mapper se este
# model não for importado).
from app.models import (  # noqa: F401
    company, client, manager, client_token, client_achievement,
    ticket, ticket_message, daily_report, subscription,
    subscription_plan, webhook, invite, enterprise_request, notification,
)

from sqlalchemy import select
from fastapi_mail import FastMail, MessageSchema, MessageType

from app.db.session import AsyncSessionLocal
from app.core.config import mail_conf
from app.models.invite import Invite, InviteStatus, InviteRole
from app.models.manager import Manager
from app.models.company import Company
from app.services.email_templates import build_invite_expired_email_html


FUNCTION_NAMES = {
    InviteRole.manager: "Gestor(a)",
    InviteRole.employee: "Colaborador(a)",
}


async def _notify_inviter(fm: FastMail, invite_row: Invite, notify_email: str) -> None:
    function_name = FUNCTION_NAMES.get(invite_row.role, "Colaborador(a)")
    html_body = build_invite_expired_email_html(invite_row.email, function_name)
    message = MessageSchema(
        subject="Convite expirado - StamFlow",
        recipients=[notify_email],
        body=html_body,
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(message)
    except Exception as e:
        # Falha no envio de e-mail não deve impedir a remoção do convite
        # vencido — registramos o erro e seguimos.
        print(f"  [ERRO] Falha ao notificar {notify_email} sobre convite expirado: {e}")


async def main():
    now = datetime.now(timezone.utc)
    fm = FastMail(mail_conf)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invite).where(
                Invite.status == InviteStatus.pending,
                Invite.expires_at < now,
            )
        )
        expirados = result.scalars().all()

        if not expirados:
            print(f"[{now.isoformat()}] expirados: 0 convite(s).")
            return

        # Invite não tem relationship() ORM para Manager/Company (só as
        # colunas de FK) — resolvemos os e-mails com queries diretas, uma
        # por manager_id/company_id distinto envolvido, em vez de N+1.
        manager_ids = {inv.manager_id for inv in expirados if inv.manager_id}
        company_ids = {inv.company_id for inv in expirados}

        managers_by_id = {}
        if manager_ids:
            res = await db.execute(select(Manager).where(Manager.id.in_(manager_ids)))
            managers_by_id = {m.id: m for m in res.scalars().all()}

        companies_by_id = {}
        if company_ids:
            res = await db.execute(select(Company).where(Company.id.in_(company_ids)))
            companies_by_id = {c.id: c for c in res.scalars().all()}

        # Resolve o destinatário do aviso ANTES de deletar: o gestor que
        # convidou (Invite.manager_id) ou, se foi a empresa que convidou
        # direto (manager_id nulo), a própria empresa.
        notificacoes = []
        for inv in expirados:
            notify_email = None
            if inv.manager_id and inv.manager_id in managers_by_id:
                notify_email = managers_by_id[inv.manager_id].email
            elif inv.company_id in companies_by_id:
                notify_email = companies_by_id[inv.company_id].email
            notificacoes.append((inv, notify_email))

        for inv in expirados:
            await db.delete(inv)
        await db.commit()

        enviados = 0
        for inv, notify_email in notificacoes:
            if notify_email:
                await _notify_inviter(fm, inv, notify_email)
                enviados += 1

        print(f"[{now.isoformat()}] expirados: {len(expirados)} convite(s) removido(s), {enviados} aviso(s) enviado(s).")


if __name__ == "__main__":
    asyncio.run(main())
