"""Add crawled_pages table for storing page content

Revision ID: 002
Revises: 001
Create Date: 2025-12-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create crawled_pages table."""
    op.create_table(
        'crawled_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('indexed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['url_id'], ['urls.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_crawled_pages_url_id', 'crawled_pages', ['url_id'], unique=True)
    op.create_index('ix_crawled_pages_indexed', 'crawled_pages', ['indexed'])


def downgrade() -> None:
    """Drop crawled_pages table."""
    op.drop_index('ix_crawled_pages_indexed', table_name='crawled_pages')
    op.drop_index('ix_crawled_pages_url_id', table_name='crawled_pages')
    op.drop_table('crawled_pages')
