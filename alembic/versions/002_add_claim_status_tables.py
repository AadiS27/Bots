"""Add claim status tables

Revision ID: 002
Revises: 001
Create Date: 2025-11-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgcrypto extension is enabled (should already exist from 001, but safe to check)
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

    # Create claim_status_queries table
    op.create_table(
        'claim_status_queries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('query_uuid', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_id', sa.BigInteger(), nullable=True),  # References claims(id) - may not exist yet
        sa.Column('payer_id', sa.BigInteger(), nullable=False),
        sa.Column('patient_id', sa.BigInteger(), nullable=True),
        sa.Column('provider_id', sa.BigInteger(), nullable=True),  # References providers(id) - may not exist yet
        
        # Query parameters
        sa.Column('member_id', sa.Text(), nullable=True),
        sa.Column('payer_claim_id', sa.Text(), nullable=True),
        sa.Column('provider_claim_id', sa.Text(), nullable=True),
        sa.Column('dos_from', sa.Date(), nullable=False),
        sa.Column('dos_to', sa.Date(), nullable=True),
        sa.Column('claim_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        
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
        # Note: claim_id and provider_id foreign keys are not added since those tables may not exist yet
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cs_queries_payer_claim', 'claim_status_queries', ['payer_id', 'payer_claim_id', 'dos_from'], unique=False)

    # Create claim_status_results table
    op.create_table(
        'claim_status_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('claim_status_query_id', sa.BigInteger(), nullable=False),
        sa.Column('claim_id', sa.BigInteger(), nullable=True),  # References claims(id) - may not exist yet
        
        # Result data
        sa.Column('high_level_status', sa.String(length=30), nullable=False),
        sa.Column('status_code', sa.String(length=20), nullable=True),
        sa.Column('status_date', sa.Date(), nullable=True),
        
        # Payment information
        sa.Column('paid_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('allowed_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('check_or_eft_number', sa.Text(), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        
        # Raw response
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        
        sa.ForeignKeyConstraint(['claim_status_query_id'], ['claim_status_queries.id'], ),
        # Note: claim_id foreign key is not added since claims table may not exist yet
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cs_results_query', 'claim_status_results', ['claim_status_query_id'], unique=False)

    # Create claim_status_reason_codes table
    op.create_table(
        'claim_status_reason_codes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('claim_status_result_id', sa.BigInteger(), nullable=False),
        sa.Column('code_type', sa.String(length=10), nullable=False),  # CARC, RARC, LOCAL
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        
        sa.ForeignKeyConstraint(['claim_status_result_id'], ['claim_status_results.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cs_reason_result', 'claim_status_reason_codes', ['claim_status_result_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index('idx_cs_reason_result', table_name='claim_status_reason_codes')
    op.drop_table('claim_status_reason_codes')
    op.drop_index('idx_cs_results_query', table_name='claim_status_results')
    op.drop_table('claim_status_results')
    op.drop_index('idx_cs_queries_payer_claim', table_name='claim_status_queries')
    op.drop_table('claim_status_queries')

