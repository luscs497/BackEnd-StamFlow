"""migration014 - corrige valor do enum demo (minusculo)

CONTEXTO DO BUG
---------------
A migration013 adicionou 'DEMO' (maiúsculo) ao enum subscription_status,
seguindo o .value do membro Python (demo = "DEMO"). Porém, o
Column(Enum(SubscriptionStatus, ...)) do SQLAlchemy, por padrão, persiste o
NOME do membro do enum (em minúsculo: 'demo', 'trialing', 'active'...), e NÃO
o .value. Prova: os valores antigos no banco são 'trialing', 'active', etc.
(minúsculo), confirmado via enum_range.

Resultado: ao inserir uma Subscription com status=SubscriptionStatus.demo, o
SQLAlchemy enviava 'demo' (minúsculo) ao Postgres, que só conhecia 'DEMO'
(maiúsculo) — erro "invalid input value for enum subscription_status: demo".

CORREÇÃO
--------
Adiciona o valor 'demo' (minúsculo) ao enum, que é o que a aplicação de fato
envia. O 'DEMO' (maiúsculo) adicionado pela migration013 fica órfão — o
Postgres não permite remover valor de enum sem recriar o tipo, e deixá-lo
sobrando é inofensivo (nenhum código jamais grava 'DEMO' maiúsculo).

Revision ID: 8c4b2e5f9a01
Revises: 7f3a9c1d4e22
Create Date: 2026-06-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8c4b2e5f9a01"
down_revision: Union[str, Sequence[str], None] = "7f3a9c1d4e22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # O valor que o SQLAlchemy realmente envia (nome do membro, minúsculo).
    op.execute("ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'demo'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres não suporta remover valor de enum sem recriar o tipo.
    # Downgrade é no-op (o valor 'demo' sobrando é inofensivo).
    pass
