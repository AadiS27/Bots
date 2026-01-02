"""SQLAlchemy ORM models for the database schema."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# Status constants
class EligibilityRequestStatus:
    """Eligibility request status values."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED_PORTAL = "FAILED_PORTAL"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_TECH = "FAILED_TECH"


class ClaimStatusQueryStatus:
    """Claim status query status values."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED_PORTAL = "FAILED_PORTAL"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_TECH = "FAILED_TECH"


class AppealsQueryStatus:
    """Appeals query status values."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED_PORTAL = "FAILED_PORTAL"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_TECH = "FAILED_TECH"


# ============================================================================
# SHARED MASTERS
# ============================================================================


class Payer(Base):
    """Insurance payer/carrier master table."""

    __tablename__ = "payers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    payer_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    enrollments: Mapped[list["PatientPayerEnrollment"]] = relationship(back_populates="payer")
    eligibility_requests: Mapped[list["EligibilityRequest"]] = relationship(back_populates="payer")


class Patient(Base):
    """Patient demographics master table."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_patient_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_line1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    enrollments: Mapped[list["PatientPayerEnrollment"]] = relationship(back_populates="patient")
    eligibility_requests: Mapped[list["EligibilityRequest"]] = relationship(back_populates="patient")


class PatientPayerEnrollment(Base):
    """Patient-payer enrollment/coverage information."""

    __tablename__ = "patient_payer_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    payer_id: Mapped[int] = mapped_column(ForeignKey("payers.id"), nullable=False)
    member_id: Mapped[str] = mapped_column(Text, nullable=False)
    group_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    coverage_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="enrollments")
    payer: Mapped["Payer"] = relationship(back_populates="enrollments")

    # Unique constraint
    __table_args__ = (Index("uq_patient_payer_member", "patient_id", "payer_id", "member_id", unique=True),)


# ============================================================================
# ELIGIBILITY WORKFLOW
# ============================================================================


class EligibilityRequest(Base):
    """Eligibility check request with status tracking."""

    __tablename__ = "eligibility_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, server_default=text("gen_random_uuid()"))
    patient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patients.id"), nullable=True)
    payer_id: Mapped[int] = mapped_column(ForeignKey("payers.id"), nullable=False)

    # Request parameters
    member_id: Mapped[str] = mapped_column(Text, nullable=False)
    group_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    service_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dos_from: Mapped[date] = mapped_column(Date, nullable=False)
    dos_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=EligibilityRequestStatus.PENDING, server_default=text(f"'{EligibilityRequestStatus.PENDING}'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    last_error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    patient: Mapped[Optional["Patient"]] = relationship(back_populates="eligibility_requests")
    payer: Mapped["Payer"] = relationship(back_populates="eligibility_requests")
    result: Mapped[Optional["EligibilityResult"]] = relationship(back_populates="request", uselist=False)

    # Indexes
    __table_args__ = (
        Index("idx_elig_req_payer_member_dos", "payer_id", "member_id", "dos_from"),
        Index("uq_elig_req_unique", "payer_id", "member_id", "dos_from", "service_type_code", "request_uuid", unique=True),
    )


class EligibilityResult(Base):
    """Eligibility check result summary."""

    __tablename__ = "eligibility_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eligibility_request_id: Mapped[int] = mapped_column(ForeignKey("eligibility_requests.id"), nullable=False, unique=True)

    # Coverage summary
    coverage_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    plan_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    coverage_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Deductibles
    deductible_individual: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    deductible_family: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    deductible_remaining_individual: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    deductible_remaining_family: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Out-of-pocket maximums
    oop_max_individual: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    oop_max_family: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Raw response
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    request: Mapped["EligibilityRequest"] = relationship(back_populates="result")
    benefit_lines: Mapped[list["EligibilityBenefitLine"]] = relationship(back_populates="result")


class EligibilityBenefitLine(Base):
    """Individual benefit line from eligibility result."""

    __tablename__ = "eligibility_benefit_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eligibility_result_id: Mapped[int] = mapped_column(ForeignKey("eligibility_results.id"), nullable=False)

    benefit_category: Mapped[str] = mapped_column(Text, nullable=False)
    service_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    network_tier: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    copay_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    coinsurance_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    deductible_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    max_benefit_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    result: Mapped["EligibilityResult"] = relationship(back_populates="benefit_lines")

    # Indexes
    __table_args__ = (Index("idx_elig_benefit_result", "eligibility_result_id"),)


# ============================================================================
# CLAIM STATUS WORKFLOW
# ============================================================================


class ClaimStatusQuery(Base):
    """Claim status inquiry request with status tracking."""

    __tablename__ = "claim_status_queries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, server_default=text("gen_random_uuid()"))
    claim_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # FK to claims(id) - table may not exist yet
    payer_id: Mapped[int] = mapped_column(ForeignKey("payers.id"), nullable=False)
    patient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patients.id"), nullable=True)
    provider_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # FK to providers(id) - table may not exist yet

    # Query parameters
    member_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payer_claim_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_claim_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dos_from: Mapped[date] = mapped_column(Date, nullable=False)
    dos_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    claim_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=ClaimStatusQueryStatus.PENDING, server_default=text(f"'{ClaimStatusQueryStatus.PENDING}'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    last_error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    payer: Mapped["Payer"] = relationship()
    patient: Mapped[Optional["Patient"]] = relationship()
    result: Mapped[Optional["ClaimStatusResult"]] = relationship(back_populates="query", uselist=False)

    # Indexes
    __table_args__ = (Index("idx_cs_queries_payer_claim", "payer_id", "payer_claim_id", "dos_from"),)


class ClaimStatusResult(Base):
    """Claim status inquiry result summary."""

    __tablename__ = "claim_status_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_status_query_id: Mapped[int] = mapped_column(ForeignKey("claim_status_queries.id"), nullable=False)
    claim_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # FK to claims(id) - table may not exist yet

    # Result data
    high_level_status: Mapped[str] = mapped_column(String(30), nullable=False)
    status_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Payment information
    paid_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    allowed_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    check_or_eft_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Raw response
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    query: Mapped["ClaimStatusQuery"] = relationship(back_populates="result")
    reason_codes: Mapped[list["ClaimStatusReasonCode"]] = relationship(back_populates="result")

    # Indexes
    __table_args__ = (Index("idx_cs_results_query", "claim_status_query_id"),)


class ClaimStatusReasonCode(Base):
    """Individual reason code from claim status result."""

    __tablename__ = "claim_status_reason_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_status_result_id: Mapped[int] = mapped_column(ForeignKey("claim_status_results.id"), nullable=False)

    code_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CARC, RARC, LOCAL
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    result: Mapped["ClaimStatusResult"] = relationship(back_populates="reason_codes")

    # Indexes
    __table_args__ = (Index("idx_cs_reason_result", "claim_status_result_id"),)


# ============================================================================
# APPEALS WORKFLOW
# ============================================================================


class AppealsQuery(Base):
    """Appeals inquiry request with status tracking."""

    __tablename__ = "appeals_queries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, server_default=text("gen_random_uuid()"))
    claim_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # FK to claims(id) - table may not exist yet
    payer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payers.id"), nullable=True)
    patient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patients.id"), nullable=True)

    # Query parameters
    search_by: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "Claim Number", "Member ID"
    search_term: Mapped[str] = mapped_column(Text, nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=AppealsQueryStatus.PENDING, server_default=text(f"'{AppealsQueryStatus.PENDING}'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    last_error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    payer: Mapped[Optional["Payer"]] = relationship()
    patient: Mapped[Optional["Patient"]] = relationship()
    result: Mapped[Optional["AppealsResult"]] = relationship(back_populates="query", uselist=False)

    # Indexes
    __table_args__ = (Index("idx_appeals_queries_search", "search_by", "search_term"),)


class AppealsResult(Base):
    """Appeals inquiry result summary."""

    __tablename__ = "appeals_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appeals_query_id: Mapped[int] = mapped_column(ForeignKey("appeals_queries.id"), nullable=False, unique=True)

    # Result data
    appeals_found: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    appeals_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Store appeals list as JSON

    # Raw response
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))

    # Relationships
    query: Mapped["AppealsQuery"] = relationship(back_populates="result")

    # Indexes
    __table_args__ = (Index("idx_appeals_results_query", "appeals_query_id"),)

# ============================================================================
# DRUG PRIOR AUTH WORKFLOW
# ============================================================================


class DrugPriorAuthQueryStatus:
    """Drug prior auth query status values."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED_PORTAL = "FAILED_PORTAL"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_TECH = "FAILED_TECH"


class DrugPriorAuthQuery(Base):
    """Drug prior authorization inquiry request with status tracking."""

    __tablename__ = "drug_prior_auth_queries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, server_default=text("gen_random_uuid()")
    )
    payer_id: Mapped[int] = mapped_column(ForeignKey("payers.id"), nullable=False)
    patient_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("patients.id"), nullable=True
    )

    # Query parameters
    organization_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # TODO: Add more fields after seeing the full form
    # member_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # drug_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ndc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=DrugPriorAuthQueryStatus.PENDING,
        server_default=text(f"'{DrugPriorAuthQueryStatus.PENDING}'"),
    )
    attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    last_error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("NOW()")
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    # Relationships
    payer: Mapped["Payer"] = relationship()
    patient: Mapped[Optional["Patient"]] = relationship()
    result: Mapped[Optional["DrugPriorAuthResult"]] = relationship(
        back_populates="query", uselist=False
    )

    # Indexes
    __table_args__ = (Index("idx_dpa_queries_payer", "payer_id"),)


class DrugPriorAuthResult(Base):
    """Drug prior authorization inquiry result summary."""

    __tablename__ = "drug_prior_auth_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    drug_prior_auth_query_id: Mapped[int] = mapped_column(
        ForeignKey("drug_prior_auth_queries.id"), nullable=False, unique=True
    )

    # Result data - TODO: Update after seeing actual results
    prior_auth_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    prior_auth_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Raw response
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    # Relationships
    query: Mapped["DrugPriorAuthQuery"] = relationship(back_populates="result")

    # Indexes
    __table_args__ = (
        Index("idx_dpa_results_query", "drug_prior_auth_query_id"),
    )