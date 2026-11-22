"""create journal_entries table

Revision ID: f4a2c9d1b7e3
Revises: 9d97981efdd9
Create Date: 2026-11-22 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a2c9d1b7e3'
down_revision: Union[str, Sequence[str], None] = '9d97981efdd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'journal_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.CheckConstraint(
            'length(trim(content)) > 0 AND length(content) <= 50000',
            name='ck_journal_entries_content_length',
        ),
        sa.CheckConstraint(
            'length(trim(title)) > 0 AND length(title) <= 200',
            name='ck_journal_entries_title_length',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_journal_entries_user_id'),
            ['user_id'],
            unique=False,
        )
        batch_op.create_index(
            'ix_journal_entries_user_id_created_at',
            ['user_id', 'created_at'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_entries_user_id_created_at')
        batch_op.drop_index(batch_op.f('ix_journal_entries_user_id'))

    op.drop_table('journal_entries')
