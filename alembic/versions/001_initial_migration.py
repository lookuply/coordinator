"""Initial migration - URL model

Revision ID: 001
Revises:
Create Date: 2025-11-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create URLs table."""
    op.create_table(
        'urls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'CRAWLING', 'COMPLETED', 'FAILED', 'SKIPPED', name='urlstatus'),
            nullable=False,
        ),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('crawl_attempts', sa.Integer(), nullable=False),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_urls_domain'), 'urls', ['domain'], unique=False)
    op.create_index(op.f('ix_urls_id'), 'urls', ['id'], unique=False)
    op.create_index(op.f('ix_urls_priority'), 'urls', ['priority'], unique=False)
    op.create_index(op.f('ix_urls_status'), 'urls', ['status'], unique=False)
    op.create_index(op.f('ix_urls_url'), 'urls', ['url'], unique=True)


def downgrade() -> None:
    """Drop URLs table."""
    op.drop_index(op.f('ix_urls_url'), table_name='urls')
    op.drop_index(op.f('ix_urls_status'), table_name='urls')
    op.drop_index(op.f('ix_urls_priority'), table_name='urls')
    op.drop_index(op.f('ix_urls_id'), table_name='urls')
    op.drop_index(op.f('ix_urls_domain'), table_name='urls')
    op.drop_table('urls')
