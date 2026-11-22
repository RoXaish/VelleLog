"""add tags and journal moods

Revision ID: b8e4f2a1c9d7
Revises: f4a2c9d1b7e3
Create Date: 2026-11-22 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4f2a1c9d7'
down_revision: Union[str, Sequence[str], None] = 'f4a2c9d1b7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MOODS = (
    "'happy'",
    "'calm'",
    "'excited'",
    "'grateful'",
    "'neutral'",
    "'sad'",
    "'anxious'",
    "'stressed'",
)
MOOD_CHECK = f"mood IS NULL OR mood IN ({', '.join(MOODS)})"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
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
            'length(trim(name)) > 0 AND length(name) <= 50',
            name='ck_tags_name_length',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_tags_user_id_name'),
    )
    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tags_user_id'), ['user_id'], unique=False)
        batch_op.create_index(
            'ix_tags_user_id_name',
            ['user_id', 'name'],
            unique=False,
        )

    op.create_table(
        'journal_entry_tags',
        sa.Column('journal_entry_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['journal_entry_id'],
            ['journal_entries.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('journal_entry_id', 'tag_id'),
    )
    with op.batch_alter_table('journal_entry_tags', schema=None) as batch_op:
        batch_op.create_index(
            'ix_journal_entry_tags_tag_id',
            ['tag_id'],
            unique=False,
        )

    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mood', sa.String(length=20), nullable=True))
        batch_op.create_check_constraint(
            'ck_journal_entries_mood',
            MOOD_CHECK,
        )
        batch_op.create_index(
            'ix_journal_entries_user_id_mood',
            ['user_id', 'mood'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_entries_user_id_mood')
        batch_op.drop_constraint('ck_journal_entries_mood', type_='check')
        batch_op.drop_column('mood')

    with op.batch_alter_table('journal_entry_tags', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_entry_tags_tag_id')

    op.drop_table('journal_entry_tags')

    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.drop_index('ix_tags_user_id_name')
        batch_op.drop_index(batch_op.f('ix_tags_user_id'))

    op.drop_table('tags')
