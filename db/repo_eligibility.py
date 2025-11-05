"""Repository for eligibility-related database operations."""

from datetime import date
from typing import Optional

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain import EligibilityBenefitLine as DomainBenefitLine
from domain import EligibilityResult as DomainResult

from .models import (
    EligibilityBenefitLine,
    EligibilityRequest,
    EligibilityRequestStatus,
    EligibilityResult,
    Patient,
    Payer,
)


async def ensure_payer(session: AsyncSession, name: str, payer_code: Optional[str] = None) -> Payer:
    """
    Get existing payer by name or create new one.

    Args:
        session: Database session
        name: Payer name
        payer_code: Optional payer code

    Returns:
        Payer instance
    """
    # Try to find existing
    stmt = select(Payer).where(Payer.name == name)
    result = await session.execute(stmt)
    payer = result.scalar_one_or_none()

    if payer is None:
        # Create new
        payer = Payer(name=name, payer_code=payer_code, is_active=True)
        session.add(payer)
        await session.flush()
        logger.info(f"Created new payer: {name} (ID: {payer.id})")
    else:
        logger.debug(f"Found existing payer: {name} (ID: {payer.id})")

    return payer


async def ensure_patient(
    session: AsyncSession,
    first_name: str,
    last_name: str,
    date_of_birth: date,
    external_patient_id: Optional[str] = None,
    **kwargs,
) -> Patient:
    """
    Get existing patient or create new one.

    Looks up by external_patient_id if provided, otherwise creates new patient.

    Args:
        session: Database session
        first_name: Patient first name
        last_name: Patient last name
        date_of_birth: Patient date of birth
        external_patient_id: Optional external patient ID for lookup
        **kwargs: Additional patient fields (gender, phone, email, address, etc.)

    Returns:
        Patient instance
    """
    patient = None

    # Try to find by external_patient_id
    if external_patient_id:
        stmt = select(Patient).where(Patient.external_patient_id == external_patient_id)
        result = await session.execute(stmt)
        patient = result.scalar_one_or_none()

    if patient is None:
        # Create new
        patient = Patient(
            external_patient_id=external_patient_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            **kwargs,
        )
        session.add(patient)
        await session.flush()
        logger.info(f"Created new patient: {last_name}, {first_name} (ID: {patient.id})")
    else:
        logger.debug(f"Found existing patient: {last_name}, {first_name} (ID: {patient.id})")

    return patient


async def enqueue_eligibility_request(
    session: AsyncSession,
    *,
    payer_id: int,
    patient_id: Optional[int],
    member_id: str,
    dos_from: date,
    service_type_code: Optional[str] = None,
    dos_to: Optional[date] = None,
    group_number: Optional[str] = None,
    coverage_type: Optional[str] = None,
) -> int:
    """
    Create a new eligibility request with PENDING status.

    Args:
        session: Database session
        payer_id: Payer ID
        patient_id: Optional patient ID
        member_id: Member ID
        dos_from: Date of service (from)
        service_type_code: Optional service type code
        dos_to: Optional date of service (to)
        group_number: Optional group number
        coverage_type: Optional coverage type

    Returns:
        Created request ID
    """
    request = EligibilityRequest(
        payer_id=payer_id,
        patient_id=patient_id,
        member_id=member_id,
        dos_from=dos_from,
        dos_to=dos_to,
        service_type_code=service_type_code,
        group_number=group_number,
        coverage_type=coverage_type,
        status=EligibilityRequestStatus.PENDING,
        attempts=0,
    )
    session.add(request)
    await session.flush()
    logger.info(f"Enqueued eligibility request ID: {request.id}")
    return request.id


async def get_next_pending_request(session: AsyncSession) -> Optional[EligibilityRequest]:
    """
    Get the next pending eligibility request and mark it as IN_PROGRESS.

    This is an atomic operation - the status update happens in the same transaction.

    Args:
        session: Database session

    Returns:
        EligibilityRequest instance or None if no pending requests
    """
    # Find oldest pending request
    stmt = (
        select(EligibilityRequest)
        .where(EligibilityRequest.status == EligibilityRequestStatus.PENDING)
        .order_by(EligibilityRequest.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)  # Lock row, skip if locked by another process
    )

    result = await session.execute(stmt)
    request = result.scalar_one_or_none()

    if request is None:
        logger.info("No pending eligibility requests found")
        return None

    # Update status to IN_PROGRESS and increment attempts
    request.status = EligibilityRequestStatus.IN_PROGRESS
    request.attempts += 1
    await session.flush()

    logger.info(f"Retrieved eligibility request ID: {request.id}, attempt #{request.attempts}")
    return request


async def mark_failed(
    session: AsyncSession,
    request_id: int,
    error_code: Optional[str],
    error_message: str,
    status: str = EligibilityRequestStatus.FAILED_TECH,
) -> None:
    """
    Mark an eligibility request as failed.

    Args:
        session: Database session
        request_id: Request ID to update
        error_code: Optional error code
        error_message: Error message
        status: Failure status (FAILED_PORTAL, FAILED_VALIDATION, FAILED_TECH)
    """
    stmt = (
        update(EligibilityRequest)
        .where(EligibilityRequest.id == request_id)
        .values(status=status, last_error_code=error_code, last_error_message=error_message)
    )
    await session.execute(stmt)
    await session.flush()
    logger.warning(f"Marked request {request_id} as {status}: {error_message}")


async def save_result(session: AsyncSession, request_id: int, result: DomainResult) -> None:
    """
    Save eligibility result and update request status to SUCCESS.

    Args:
        session: Database session
        request_id: Request ID
        result: Domain EligibilityResult object
    """
    # Create result header
    db_result = EligibilityResult(
        eligibility_request_id=request_id,
        coverage_status=result.coverage_status,
        plan_name=result.plan_name,
        plan_type=result.plan_type,
        coverage_start_date=result.coverage_start_date,
        coverage_end_date=result.coverage_end_date,
        deductible_individual=result.deductible_individual,
        deductible_remaining_individual=result.deductible_remaining_individual,
        oop_max_individual=result.oop_max_individual,
        oop_max_family=result.oop_max_family,
        raw_response={"html_path": result.raw_response_html_path} if result.raw_response_html_path else None,
    )
    session.add(db_result)
    await session.flush()

    # Create benefit lines
    for benefit_line in result.benefit_lines:
        db_benefit = EligibilityBenefitLine(
            eligibility_result_id=db_result.id,
            benefit_category=benefit_line.benefit_category,
            service_type_code=benefit_line.service_type_code,
            network_tier=benefit_line.network_tier,
            copay_amount=benefit_line.copay_amount,
            coinsurance_percent=benefit_line.coinsurance_percent,
            deductible_amount=benefit_line.deductible_amount,
            max_benefit_amount=benefit_line.max_benefit_amount,
            notes=benefit_line.notes,
        )
        session.add(db_benefit)

    # Update request status to SUCCESS
    stmt = (
        update(EligibilityRequest)
        .where(EligibilityRequest.id == request_id)
        .values(status=EligibilityRequestStatus.SUCCESS, last_error_code=None, last_error_message=None)
    )
    await session.execute(stmt)
    await session.flush()

    logger.info(f"Saved result for request {request_id} with {len(result.benefit_lines)} benefit lines")


async def get_request_by_id(session: AsyncSession, request_id: int) -> Optional[EligibilityRequest]:
    """
    Get eligibility request by ID with relationships loaded.

    Args:
        session: Database session
        request_id: Request ID

    Returns:
        EligibilityRequest instance or None
    """
    stmt = select(EligibilityRequest).where(EligibilityRequest.id == request_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

