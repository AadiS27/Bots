"""Repository for claim status-related database operations."""

from datetime import date
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.claim_status_models import ClaimStatusReason as DomainReason
from domain.claim_status_models import ClaimStatusResult as DomainResult

from .models import (
    ClaimStatusQuery,
    ClaimStatusQueryStatus,
    ClaimStatusReasonCode,
    ClaimStatusResult,
)


async def enqueue_claim_status_query(
    session: AsyncSession,
    *,
    payer_id: int,
    claim_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    member_id: Optional[str] = None,
    payer_claim_id: Optional[str] = None,
    provider_claim_id: Optional[str] = None,
    dos_from: date,
    dos_to: Optional[date] = None,
    claim_amount: Optional[Decimal] = None,
) -> int:
    """
    Create a new claim status query with PENDING status.

    Args:
        session: Database session
        payer_id: Payer ID
        claim_id: Optional claim ID
        patient_id: Optional patient ID
        provider_id: Optional provider ID
        member_id: Optional member ID
        payer_claim_id: Optional payer claim ID
        provider_claim_id: Optional provider claim ID
        dos_from: Date of service (from)
        dos_to: Optional date of service (to)
        claim_amount: Optional claim amount

    Returns:
        Created query ID
    """
    query = ClaimStatusQuery(
        payer_id=payer_id,
        claim_id=claim_id,
        patient_id=patient_id,
        provider_id=provider_id,
        member_id=member_id,
        payer_claim_id=payer_claim_id,
        provider_claim_id=provider_claim_id,
        dos_from=dos_from,
        dos_to=dos_to,
        claim_amount=float(claim_amount) if claim_amount else None,
        status=ClaimStatusQueryStatus.PENDING,
        attempts=0,
    )
    session.add(query)
    await session.flush()
    logger.info(f"Enqueued claim status query ID: {query.id}")
    return query.id


async def get_next_pending_query(session: AsyncSession) -> Optional[ClaimStatusQuery]:
    """
    Get the next pending claim status query and mark it as IN_PROGRESS.

    This is an atomic operation - the status update happens in the same transaction.

    Args:
        session: Database session

    Returns:
        ClaimStatusQuery instance or None if no pending queries
    """
    # Find oldest pending query
    stmt = (
        select(ClaimStatusQuery)
        .where(ClaimStatusQuery.status == ClaimStatusQueryStatus.PENDING)
        .order_by(ClaimStatusQuery.requested_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)  # Lock row, skip if locked by another process
    )

    result = await session.execute(stmt)
    query = result.scalar_one_or_none()

    if query is None:
        logger.info("No pending claim status queries found")
        return None

    # Update status to IN_PROGRESS and increment attempts
    query.status = ClaimStatusQueryStatus.IN_PROGRESS
    query.attempts += 1
    await session.flush()

    logger.info(f"Retrieved claim status query ID: {query.id}, attempt #{query.attempts}")
    return query


async def mark_failed(
    session: AsyncSession,
    query_id: int,
    code: Optional[str],
    message: str,
    status: str = ClaimStatusQueryStatus.FAILED_TECH,
) -> None:
    """
    Mark a claim status query as failed.

    Args:
        session: Database session
        query_id: Query ID to update
        code: Optional error code
        message: Error message
        status: Failure status (FAILED_PORTAL, FAILED_VALIDATION, FAILED_TECH)
    """
    stmt = (
        update(ClaimStatusQuery)
        .where(ClaimStatusQuery.id == query_id)
        .values(status=status, last_error_code=code, last_error_message=message)
    )
    await session.execute(stmt)
    await session.flush()
    logger.warning(f"Marked claim status query {query_id} as {status}: {message}")


async def save_claim_status_result(
    session: AsyncSession,
    query_id: int,
    result_data: DomainResult,
    raw_response: Optional[dict] = None,
) -> None:
    """
    Save claim status result and update query status to SUCCESS.

    Args:
        session: Database session
        query_id: Query ID
        result_data: Domain ClaimStatusResult object
        raw_response: Optional raw response dictionary
    """
    # Create result header
    # Note: high_level_status is required in DB but may be None in domain model
    # Use a default value if None
    high_level_status = result_data.high_level_status or "UNKNOWN"

    db_result = ClaimStatusResult(
        claim_status_query_id=query_id,
        high_level_status=high_level_status,
        status_code=result_data.status_code,
        status_date=result_data.status_date,
        paid_amount=result_data.paid_amount,
        allowed_amount=result_data.allowed_amount,
        check_or_eft_number=result_data.check_or_eft_number,
        payment_date=result_data.payment_date,
        raw_response=raw_response or ({"html_path": result_data.raw_response_html_path} if result_data.raw_response_html_path else None),
    )
    session.add(db_result)
    await session.flush()

    # Create reason codes
    for reason_code in result_data.reason_codes:
        db_reason = ClaimStatusReasonCode(
            claim_status_result_id=db_result.id,
            code_type=reason_code.code_type,
            code=reason_code.code,
            description=reason_code.description,
        )
        session.add(db_reason)

    # Update query status to SUCCESS and set completed_at
    from datetime import datetime

    stmt = (
        update(ClaimStatusQuery)
        .where(ClaimStatusQuery.id == query_id)
        .values(
            status=ClaimStatusQueryStatus.SUCCESS,
            completed_at=datetime.now(),
            last_error_code=None,
            last_error_message=None,
        )
    )
    await session.execute(stmt)
    await session.flush()

    logger.info(f"Saved claim status result for query {query_id} with {len(result_data.reason_codes)} reason codes")


async def get_query_by_id(session: AsyncSession, query_id: int) -> Optional[ClaimStatusQuery]:
    """
    Get claim status query by ID with relationships loaded.

    Args:
        session: Database session
        query_id: Query ID

    Returns:
        ClaimStatusQuery instance or None
    """
    stmt = select(ClaimStatusQuery).where(ClaimStatusQuery.id == query_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

