"""migration013 - demo de 7 dias (status DEMO + controle de uso)

Adiciona o status DEMO ao enum subscription_status, distinto de TRIALING.

Por quê um status novo em vez de reaproveitar TRIALING:
TRIALING já existe e está documentado (subscription_service.start_trial) como
"teste grátis de 7 dias, produto completo, não demo" — reservado para um
eventual trial completo futuro (ex.: para empresas). O modo demo decidido
agora é deliberadamente LIMITADO (sem Pausa Mental, sem Foco, sem University,
sem Relatórios, exercícios guiados limitados) e SEM armazenar métricas de
uso reais. Misturar os dois no mesmo status faria o backend (e qualquer
relatório futuro) não conseguir distinguir "trial completo" de "demo
limitado" sem heurística adicional. Um enum novo deixa a intenção explícita
e a checagem de acesso (check_active_subscription / frontend) simples.

Também adiciona em "clients":
  - demo_used_at: data em que a conta consumiu o demo (mesmo padrão de
    trial_used_at). Controla "1 demo por conta/por vida".
  - last_activity_at: última atividade da conta (login, sync, etc.) — usado
    pelo job de limpeza de contas demo inativas há mais de 90 dias.

Revision ID: 7f3a9c1d4e22
Revises: 2bde43f96589
Create Date: 2026-06-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f3a9c1d4e22"
down_revision: Union[str, Sequence[str], None] = "2bde43f96589"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona o novo valor ao enum existente (Postgres exige ALTER TYPE
    # fora de uma transação implícita de DDL composta; op.execute cobre isso
    # corretamente via alembic).
    op.execute("ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'DEMO'")

    op.add_column(
        "clients",
        sa.Column("demo_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("clients", "last_activity_at")
    op.drop_column("clients", "demo_used_at")
    # Observação: Postgres não suporta remover valor de enum diretamente
    # (precisaria recriar o tipo). Deixamos o valor DEMO no enum no downgrade
    # — não causa problema funcional ficar "sobrando" um valor não utilizado.
