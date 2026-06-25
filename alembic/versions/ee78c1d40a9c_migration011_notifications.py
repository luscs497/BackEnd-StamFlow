"""migration011 - notifications

Revision ID: ee78c1d40a9c
Revises: 16261ed2862b
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee78c1d40a9c'
down_revision: Union[str, Sequence[str], None] = '16261ed2862b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('client_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'tipo',
            sa.Enum(
                'report_respondido',
                'relatorio_semanal',
                'convite_expirado',
                'pausa_recomendada',
                'postura_critica',
                'postura_atencao',
                name='notification_type',
            ),
            nullable=False,
        ),
        sa.Column('titulo', sa.String(length=120), nullable=False),
        sa.Column('mensagem', sa.String(length=500), nullable=False),
        sa.Column('link_destino', sa.String(length=255), nullable=True),
        sa.Column('lida', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('lida_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(
        'ix_notifications_client_criada',
        'notifications',
        ['client_id', 'criada_em'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notifications_client_criada', table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    # Remove o tipo enum criado para a tabela (Postgres).
    sa.Enum(name='notification_type').drop(op.get_bind(), checkfirst=True)
