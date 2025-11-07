"""Repository for appeals-related database operations."""

from typing import Optional

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.appeals_models import AppealsResult as DomainResult

from .models import AppealsQuery, AppealsQueryStatus, AppealsResult


async def enqueue_appeals_query(
    session: AsyncSession,
    *,
    search_by: str,
    search_term: str,
    payer_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    claim_id: Optional[int] = None,
) -> int:
    """
    Create a new appeals query with PENDING status.

    Args:
        session: Database session
        search_by: Search criteria type (e.g., "Claim Number", "Member ID")
        search_term: Search term value
        payer_id: Optional payer ID
        patient_id: Optional patient ID
        claim_id: Optional claim ID

    Returns:
        Created query ID
    """
    query = AppealsQuery(
        search_by=search_by,
        search_term=search_term,
        payer_id=payer_id,
        patient_id=patient_id,
        claim_id=claim_id,
        status=AppealsQueryStatus.PENDING,
        attempts=0,
    )
    session.add(query)
    await session.flush()
    logger.info(f"Enqueued appeals query ID: {query.id}")
    return query.id


async def get_next_pending_query(session: AsyncSession) -> Optional[AppealsQuery]:
    """
    Get the next pending appeals query and mark it as IN_PROGRESS.

    This is an atomic operation - the status update happens in the same transaction.

    Args:
        session: Database session

    Returns:
        AppealsQuery instance or None if no pending queries
    """
    # Find oldest pending query
    stmt = (
        select(AppealsQuery)
        .where(AppealsQuery.status == AppealsQueryStatus.PENDING)
        .order_by(AppealsQuery.requested_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)  # Lock row, skip if locked by another process
    )

    result = await session.execute(stmt)
    query = result.scalar_one_or_none()

    if query is None:
        logger.info("No pending appeals queries found")
        return None

    # Update status to IN_PROGRESS and increment attempts
    query.status = AppealsQueryStatus.IN_PROGRESS
    query.attempts += 1
    await session.flush()

    logger.info(f"Retrieved appeals query ID: {query.id}, attempt #{query.attempts}")
    return query


async def mark_failed(
    session: AsyncSession,
    query_id: int,
    code: Optional[str],
    message: str,
    status: str = AppealsQueryStatus.FAILED_TECH,
) -> None:
    """
    Mark an appeals query as failed.

    Args:
        session: Database session
        query_id: Query ID to update
        code: Optional error code
        message: Error message
        status: Failure status (FAILED_PORTAL, FAILED_VALIDATION, FAILED_TECH)
    """
    stmt = (
        update(AppealsQuery)
        .where(AppealsQuery.id == query_id)
        .values(status=status, last_error_code=code, last_error_message=message)
    )
    await session.execute(stmt)
    await session.flush()
    logger.warning(f"Marked appeals query {query_id} as {status}: {message}")


async def save_appeals_result(
    session: AsyncSession,
    query_id: int,
    result_data: DomainResult,
    raw_response: Optional[dict] = None,
) -> None:
    """
    Save appeals result and update query status to SUCCESS.

    Args:
        session: Database session
        query_id: Query ID
        result_data: Domain AppealsResult object
        raw_response: Optional raw response dictionary
    """
    # Create result
    db_result = AppealsResult(
        appeals_query_id=query_id,
        appeals_found=result_data.appeals_found,
        appeals_data={"appeals": result_data.appeals} if result_data.appeals else None,
        raw_response=raw_response or ({"html_path": result_data.raw_response_html_path} if result_data.raw_response_html_path else None),
    )
    session.add(db_result)
    await session.flush()

    # Update query status to SUCCESS and set completed_at
    from datetime import datetime

    stmt = (
        update(AppealsQuery)
        .where(AppealsQuery.id == query_id)
        .values(
            status=AppealsQueryStatus.SUCCESS,
            completed_at=datetime.now(),
            last_error_code=None,
            last_error_message=None,
        )
    )
    await session.execute(stmt)
    await session.flush()

    logger.info(f"Saved appeals result for query {query_id} with {result_data.appeals_found} appeals found")


async def get_query_by_id(session: AsyncSession, query_id: int) -> Optional[AppealsQuery]:
    """
    Get appeals query by ID with relationships loaded.

    Args:
        session: Database session
        query_id: Query ID

    Returns:
        AppealsQuery instance or None
    """
    stmt = select(AppealsQuery).where(AppealsQuery.id == query_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

