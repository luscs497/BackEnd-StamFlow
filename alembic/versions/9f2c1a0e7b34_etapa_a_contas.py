"""etapa A - contas/planos: trial_used_at + enterprise_requests

Revision ID: 9f2c1a0e7b34
Revises: 16261ed2862b
Create Date: 2026-06-18

Adiciona:
  - clients.trial_used_at  (controle do teste grátis: 1 por conta)
  - tabela enterprise_requests (funil de pedidos de plano empresarial)
"""
from alembic import op
import sqlalchemy as sa


# identificadores da migração
revision = "9f2c1a0e7b34"
down_revision = "16261ed2862b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Teste grátis: marca quando a conta consumiu o trial (NULL = nunca usou)
    op.add_column(
        "clients",
        sa.Column("trial_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2) Funil de solicitações empresariais (sem checkout automático)
    op.create_table(
        "enterprise_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True, index=True),
        sa.Column("nome_empresa", sa.String(length=255), nullable=False),
        sa.Column("contato_nome", sa.String(length=120), nullable=False),
        sa.Column("contato_email", sa.String(length=120), nullable=True),
        sa.Column("contato_whatsapp", sa.String(length=20), nullable=True),
        sa.Column("qtd_colaboradores", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qtd_gestores", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pendente_proposta", "negociando", "aprovado",
                "provisionado", "recusado",
                name="enterprise_request_status",
            ),
            nullable=False,
            server_default="pendente_proposta",
        ),
        sa.Column(
            "company_id",
            sa.BigInteger(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("enterprise_requests")
    op.execute("DROP TYPE IF EXISTS enterprise_request_status")
    op.drop_column("clients", "trial_used_at")
