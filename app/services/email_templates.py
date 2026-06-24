"""
Templates de e-mail do StamFlow.

Centraliza o HTML dos e-mails transacionais para manter consistência visual
(o mesmo cartão escuro com barra de gradiente no topo, usado no e-mail de
redefinição de senha em main.py) sem duplicar o markup em cada lugar que
dispara um e-mail.
"""


def _card_shell(title: str, subtitle: str, body_html: str) -> str:
    """
    Estrutura de cartão compartilhada por todos os e-mails transacionais.
    `body_html` é o conteúdo específico de cada e-mail (parágrafos, botão,
    avisos), já formatado em HTML.
    """
    return f"""
    <div style="margin:0;padding:0;background-color:#0b1120;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0b1120;padding:32px 0;">
        <tr><td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#0f172a;border-radius:16px;overflow:hidden;border:1px solid #1e293b;">
            <tr><td style="height:6px;background-color:#a855f7;background-image:linear-gradient(90deg,#38bdf8,#a855f7,#ec4899,#f59e0b);font-size:0;line-height:0;">&nbsp;</td></tr>
            <tr><td style="padding:36px 36px 28px 36px;font-family:Arial,Helvetica,sans-serif;color:#e2e8f0;">
              <img src="https://login.stamflow.com.br/icon.png" width="48" height="48" alt="StamFlow" style="border-radius:14px;display:block;margin-bottom:14px;" />
              <div style="font-size:22px;font-weight:bold;color:#ffffff;margin-bottom:2px;">{title}</div>
              <div style="font-size:14px;color:#94a3b8;margin-bottom:24px;">{subtitle}</div>
              {body_html}
            </td></tr>
          </table>
          <div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#475569;margin-top:16px;">&copy; StamFlow</div>
        </td></tr>
      </table>
    </div>
    """


def _cta_button(href: str, label: str) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">
      <tr><td align="center" style="border-radius:10px;background-color:#7c3aed;background-image:linear-gradient(90deg,#6366f1,#a855f7,#ec4899);">
        <a href="{href}" style="display:inline-block;padding:14px 32px;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:10px;">{label}</a>
      </td></tr>
    </table>
    """


def build_invite_email_html(register_link: str, function_name: str, expires_in_label: str = "24 horas", name: str | None = None) -> str:
    """
    E-mail enviado ao convidado (funcionário ou gestor) com o link para criar
    a conta. Mesmo "shell" visual do e-mail de redefinição de senha.
    """
    greeting = f"Olá, {name}" if name else "Olá"
    body = f"""
    <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 16px 0;">{greeting},</p>
    <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 24px 0;">Você foi convidado(a) para se juntar ao StamFlow como <strong>{function_name}</strong>. Clique no botão abaixo para criar sua conta e acessar a plataforma:</p>
    {_cta_button(register_link, "Criar minha conta")}
    <p style="font-size:13px;line-height:1.6;color:#94a3b8;margin:0 0 6px 0;">Ou copie e cole este link no navegador:</p>
    <p style="font-size:13px;line-height:1.5;color:#38bdf8;word-break:break-all;margin:0 0 24px 0;">{register_link}</p>
    <div style="border-top:1px solid #1e293b;padding-top:16px;">
      <p style="font-size:12px;color:#64748b;margin:0 0 4px 0;">Este link expira em {expires_in_label}.</p>
      <p style="font-size:12px;color:#64748b;margin:0;">Se você não esperava este convite, pode ignorar este e-mail.</p>
    </div>
    """
    return _card_shell("StamFlow", "Convite para a plataforma", body)


def build_invite_expired_email_html(invitee_email: str, function_name: str) -> str:
    """
    E-mail enviado a quem ENVIOU o convite (gestor ou empresa), avisando que
    o convidado não aceitou a tempo e o convite foi removido da lista.
    """
    body = f"""
    <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 16px 0;">Olá,</p>
    <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 24px 0;">
        O convite enviado para <strong>{invitee_email}</strong> (como {function_name}) expirou sem ser aceito
        e foi removido da sua lista de colaboradores.
    </p>
    <p style="font-size:15px;line-height:1.6;color:#cbd5e1;margin:0 0 24px 0;">
        Se ainda quiser convidar essa pessoa, você pode enviar um novo convite a qualquer momento pelo painel.
    </p>
    <div style="border-top:1px solid #1e293b;padding-top:16px;">
      <p style="font-size:12px;color:#64748b;margin:0;">Este é um aviso automático do StamFlow.</p>
    </div>
    """
    return _card_shell("StamFlow", "Convite expirado", body)
