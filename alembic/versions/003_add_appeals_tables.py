"""Add appeals tables

Revision ID: 003
Revises: 002
Create Date: 2025-11-07 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgcrypto extension is enabled (should already exist from 001, but safe to check)
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

    # Create appeals_queries table
    op.create_table(
        'appeals_queries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('query_uuid', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_id', sa.BigInteger(), nullable=True),  # References claims(id) - may not exist yet
        sa.Column('payer_id', sa.BigInteger(), nullable=True),
        sa.Column('patient_id', sa.BigInteger(), nullable=True),
        
        # Query parameters
        sa.Column('search_by', sa.Text(), nullable=False),  # e.g., "Claim Number", "Member ID"
        sa.Column('search_term', sa.Text(), nullable=False),
        
        # Status tracking
        sa.Column('status', sa.String(length=30), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column('attempts', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_error_code', sa.Text(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        
        sa.ForeignKeyConstraint(['payer_id'], ['payers.id'], ),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        # Note: claim_id foreign key is not added since claims table may not exist yet
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_appeals_queries_search', 'appeals_queries', ['search_by', 'search_term'], unique=False)

    # Create appeals_results table
    op.create_table(
        'appeals_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('appeals_query_id', sa.BigInteger(), nullable=False),
        
        # Result data
        sa.Column('appeals_found', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('appeals_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # Store appeals list as JSON
        
        # Raw response
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        
        sa.ForeignKeyConstraint(['appeals_query_id'], ['appeals_queries.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('appeals_query_id')
    )
    op.create_index('idx_appeals_results_query', 'appeals_results', ['appeals_query_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index('idx_appeals_results_query', table_name='appeals_results')
    op.drop_table('appeals_results')
    op.drop_index('idx_appeals_queries_search', table_name='appeals_queries')
    op.drop_table('appeals_queries')

