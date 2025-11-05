"""Initial schema with shared masters and eligibility tables

Revision ID: 001
Revises: 
Create Date: 2025-11-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto extension for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

    # Create payers table
    op.create_table(
        'payers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('payer_code', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('external_patient_id', sa.Text(), nullable=True),
        sa.Column('first_name', sa.Text(), nullable=False),
        sa.Column('last_name', sa.Text(), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('phone', sa.String(length=25), nullable=True),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('address_line1', sa.Text(), nullable=True),
        sa.Column('address_line2', sa.Text(), nullable=True),
        sa.Column('city', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('postal_code', sa.String(length=15), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_patient_id')
    )

    # Create patient_payer_enrollments table
    op.create_table(
        'patient_payer_enrollments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('patient_id', sa.BigInteger(), nullable=False),
        sa.Column('payer_id', sa.BigInteger(), nullable=False),
        sa.Column('member_id', sa.Text(), nullable=False),
        sa.Column('group_number', sa.Text(), nullable=True),
        sa.Column('plan_name', sa.Text(), nullable=True),
        sa.Column('coverage_start_date', sa.Date(), nullable=True),
        sa.Column('coverage_end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['payers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_patient_payer_member', 'patient_payer_enrollments', ['patient_id', 'payer_id', 'member_id'], unique=True)

    # Create eligibility_requests table
    op.create_table(
        'eligibility_requests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_uuid', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', sa.BigInteger(), nullable=True),
        sa.Column('payer_id', sa.BigInteger(), nullable=False),
        sa.Column('member_id', sa.Text(), nullable=False),
        sa.Column('group_number', sa.Text(), nullable=True),
        sa.Column('service_type_code', sa.String(length=10), nullable=True),
        sa.Column('coverage_type', sa.String(length=20), nullable=True),
        sa.Column('dos_from', sa.Date(), nullable=False),
        sa.Column('dos_to', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=30), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column('attempts', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_error_code', sa.Text(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['payers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_elig_req_payer_member_dos', 'eligibility_requests', ['payer_id', 'member_id', 'dos_from'], unique=False)
    op.create_index('uq_elig_req_unique', 'eligibility_requests', ['payer_id', 'member_id', 'dos_from', 'service_type_code', 'request_uuid'], unique=True)

    # Create eligibility_results table
    op.create_table(
        'eligibility_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('eligibility_request_id', sa.BigInteger(), nullable=False),
        sa.Column('coverage_status', sa.String(length=30), nullable=True),
        sa.Column('plan_name', sa.Text(), nullable=True),
        sa.Column('plan_type', sa.Text(), nullable=True),
        sa.Column('coverage_start_date', sa.Date(), nullable=True),
        sa.Column('coverage_end_date', sa.Date(), nullable=True),
        sa.Column('deductible_individual', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('deductible_family', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('deductible_remaining_individual', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('deductible_remaining_family', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('oop_max_individual', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('oop_max_family', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['eligibility_request_id'], ['eligibility_requests.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('eligibility_request_id')
    )

    # Create eligibility_benefit_lines table
    op.create_table(
        'eligibility_benefit_lines',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('eligibility_result_id', sa.BigInteger(), nullable=False),
        sa.Column('benefit_category', sa.Text(), nullable=False),
        sa.Column('service_type_code', sa.String(length=10), nullable=True),
        sa.Column('network_tier', sa.String(length=30), nullable=True),
        sa.Column('copay_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('coinsurance_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('deductible_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_benefit_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['eligibility_result_id'], ['eligibility_results.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_elig_benefit_result', 'eligibility_benefit_lines', ['eligibility_result_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_elig_benefit_result', table_name='eligibility_benefit_lines')
    op.drop_table('eligibility_benefit_lines')
    op.drop_table('eligibility_results')
    op.drop_index('uq_elig_req_unique', table_name='eligibility_requests')
    op.drop_index('idx_elig_req_payer_member_dos', table_name='eligibility_requests')
    op.drop_table('eligibility_requests')
    op.drop_index('uq_patient_payer_member', table_name='patient_payer_enrollments')
    op.drop_table('patient_payer_enrollments')
    op.drop_table('patients')
    op.drop_table('payers')
    op.execute('DROP EXTENSION IF EXISTS pgcrypto;')

