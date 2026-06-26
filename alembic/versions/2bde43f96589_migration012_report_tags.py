"""migration012 - report tags (operational / hr_management / legal)

Revision ID: 2bde43f96589
Revises: ee78c1d40a9c
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bde43f96589'
down_revision: Union[str, Sequence[str], None] = 'ee78c1d40a9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    report_tag_enum = sa.Enum(
        'operational', 'hr_management', 'legal',
        name='report_tag',
    )
    report_tag_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'tickets',
        sa.Column(
            'tag',
            report_tag_enum,
            nullable=False,
            server_default='operational',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tickets', 'tag')
    sa.Enum(name='report_tag').drop(op.get_bind(), checkfirst=True)
