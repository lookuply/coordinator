"""add evaluation workflow fields

Revision ID: 003
Revises: 002
Create Date: 2025-12-18

Add AI evaluation workflow fields to crawled_pages table:
- ai_score: Quality score 0-100
- summary: AI-generated page summary
- evaluation_status: Workflow status tracking
- evaluated_at: Evaluation timestamp
- evaluation_error: Error message if evaluation failed
- depth: Crawl depth tracking
- parent_url_id: Parent URL reference for link discovery

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add evaluation workflow fields to crawled_pages."""
    # Add AI evaluation fields
    op.add_column('crawled_pages', sa.Column('ai_score', sa.Integer(), nullable=True))
    op.add_column('crawled_pages', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('crawled_pages', sa.Column(
        'evaluation_status',
        sa.String(length=20),
        nullable=False,
        server_default='pending'
    ))
    op.add_column('crawled_pages', sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('crawled_pages', sa.Column('evaluation_error', sa.Text(), nullable=True))

    # Add crawl depth tracking fields
    op.add_column('crawled_pages', sa.Column('depth', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('crawled_pages', sa.Column('parent_url_id', sa.Integer(), nullable=True))

    # Create indexes for performance
    op.create_index('ix_crawled_pages_ai_score', 'crawled_pages', ['ai_score'])
    op.create_index('ix_crawled_pages_evaluation_status', 'crawled_pages', ['evaluation_status'])
    op.create_index('ix_crawled_pages_depth', 'crawled_pages', ['depth'])

    # Add foreign key constraint for parent_url_id
    op.create_foreign_key(
        'fk_crawled_pages_parent_url_id',
        'crawled_pages', 'urls',
        ['parent_url_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Remove evaluation workflow fields from crawled_pages."""
    # Drop foreign key
    op.drop_constraint('fk_crawled_pages_parent_url_id', 'crawled_pages', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_crawled_pages_depth', 'crawled_pages')
    op.drop_index('ix_crawled_pages_evaluation_status', 'crawled_pages')
    op.drop_index('ix_crawled_pages_ai_score', 'crawled_pages')

    # Drop columns
    op.drop_column('crawled_pages', 'parent_url_id')
    op.drop_column('crawled_pages', 'depth')
    op.drop_column('crawled_pages', 'evaluation_error')
    op.drop_column('crawled_pages', 'evaluated_at')
    op.drop_column('crawled_pages', 'evaluation_status')
    op.drop_column('crawled_pages', 'summary')
    op.drop_column('crawled_pages', 'ai_score')
