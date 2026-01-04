"""FastAPI server for Availity bots API."""

import asyncio
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from loguru import logger
from rich.console import Console

from api.models import (
    ClaimStatusRequest, ClaimStatusResponse,
    ClaimsRequest, ClaimsResponse,
    EligibilityRequest, EligibilityResponse,
    ErrorResponse
)
from api.driver_manager import WebDriverManager
from bots import ClaimsBot, ClaimStatusBot, EligibilityBot
from config import settings
from core import (
    PortalBusinessError,
    PortalChangedError,
    TransientError,
    ValidationError,
    setup_logging,
    set_request_id,
    clear_request_id,
)
from domain.claims_models import ClaimsQuery, ServiceLine
from domain.claim_status_models import ClaimStatusQuery
from domain.eligibility_models import EligibilityRequest as EligibilityRequestModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Availity Bots API server...")
    # Keep-alive will start automatically when driver is first created
    yield
    # Shutdown
    logger.info("Shutting down Availity Bots API server...")
    driver_manager.close()

app = FastAPI(
    title="Availity Bots API",
    description="API for automated Availity portal operations (Claims, Claim Status, Eligibility, Appeals)",
    version="1.0.0",
    lifespan=lifespan  # Add lifespan handler
)

console = Console()
setup_logging(log_level="INFO")

# Store for request status (in production, use Redis or database)
request_status_store = {}

# Shared WebDriver manager instance
driver_manager = WebDriverManager.get_instance()


def convert_date_format(date_str: str, from_format: str = "YYYYMMDD", to_format: str = "YYYY-MM-DD") -> str:
    """Convert date from YYYYMMDD to YYYY-MM-DD."""
    if from_format == "YYYYMMDD" and to_format == "YYYY-MM-DD":
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def process_claim_status_sync(request: ClaimStatusRequest) -> dict:
    """Process claim status check synchronously."""
    try:
        set_request_id(request.request_id)
        
        # Convert API request to domain model (already in correct format)
        dos_from = datetime.strptime(request.dos_from, "%Y-%m-%d").date()
        dos_to = None
        if request.dos_to:
            dos_to = datetime.strptime(request.dos_to, "%Y-%m-%d").date()
        
        patient_dob = None
        if request.patient_dob:
            patient_dob = datetime.strptime(request.patient_dob, "%Y-%m-%d").date()
        
        query = ClaimStatusQuery(
            request_id=request.request_id,
            payer_name=request.payer_name,
            payer_claim_id=request.payer_claim_id,
            provider_claim_id=request.provider_claim_id,
            member_id=request.member_id,
            patient_last_name=request.patient_last_name,
            patient_first_name=request.patient_first_name,
            patient_dob=patient_dob,
            subscriber_last_name=request.subscriber_last_name,
            subscriber_first_name=request.subscriber_first_name,
            subscriber_same_as_patient=request.subscriber_same_as_patient,
            provider_npi=request.provider_npi,
            dos_from=dos_from,
            dos_to=dos_to,
            claim_amount=request.claim_amount,
        )
        
        # Acquire exclusive access to shared WebDriver instance
        shared_driver = driver_manager.acquire_driver(headless=False)
        
        # Run bot with shared driver
        bot = ClaimStatusBot(
            base_url=settings.BASE_URL,
            username=settings.USERNAME,
            password=settings.PASSWORD,
            headless=False,  # Show browser for debugging
            artifacts_dir=settings.ARTIFACTS_DIR,
            driver=shared_driver,  # Use shared driver
        )
        
        try:
            result = bot.process_query(query)
            
            return {
                "request_id": request.request_id,
                "transaction_id": result.transaction_id,
                "high_level_status": result.high_level_status,
                "status_code": result.status_code,
                "finalized_date": str(result.finalized_date) if result.finalized_date else None,
                "service_dates": result.service_dates,
                "claim_number": result.claim_number,
                "member_name": result.member_name,
                "member_id": result.member_id,
                "billed_amount": result.billed_amount,
                "paid_amount": result.paid_amount,
                "check_or_eft_number": result.check_or_eft_number,
                "payment_date": str(result.payment_date) if result.payment_date else None,
                "reason_codes": [
                    {
                        "code_type": rc.code_type,
                        "code": rc.code,
                        "description": rc.description
                    } for rc in result.reason_codes
                ] if result.reason_codes else [],
            }
        finally:
            bot.close()  # This won't close the shared driver
            driver_manager.release_driver()  # Release exclusive access
            clear_request_id()
            
    except Exception as e:
        driver_manager.release_driver()  # Release exclusive access on error
        clear_request_id()
        error_msg = str(e)
        logger.error(f"Error processing claim status: {e}")
        return {
            "request_id": request.request_id,
            "transaction_id": None,
            "high_level_status": None,
            "status_code": None,
            "finalized_date": None,
            "service_dates": None,
            "claim_number": None,
            "member_name": None,
            "member_id": None,
            "billed_amount": None,
            "paid_amount": None,
            "check_or_eft_number": None,
            "payment_date": None,
            "reason_codes": [],
        }


def process_claims_sync(request: ClaimsRequest, request_id: str) -> dict:
    """Process claims submission synchronously."""
    try:
        # Generate integer request ID from UUID hash
        request_id_int = int(hashlib.md5(request_id.encode()).hexdigest()[:8], 16) % 1000000000
        set_request_id(request_id_int)
        
        # Convert API request to domain model
        subscriber_dob = datetime.strptime(convert_date_format(request.subscriber.dateOfBirth), "%Y-%m-%d").date()
        
        provider = request.providers[0] if request.providers else None
        
        # Parse provider name (handle "Last, First" or just "Name" format)
        billing_provider_last_name = None
        billing_provider_first_name = None
        if provider and provider.organizationName:
            if ", " in provider.organizationName:
                parts = provider.organizationName.split(", ", 1)
                billing_provider_last_name = parts[0]
                billing_provider_first_name = parts[1] if len(parts) > 1 else None
            else:
                billing_provider_last_name = provider.organizationName
        
        # Parse service lines
        service_lines = []
        if request.serviceLines:
            for sl in request.serviceLines:
                sl_from_date = datetime.strptime(sl.fromDate, "%Y-%m-%d").date()
                service_lines.append(ServiceLine(
                    from_date=sl_from_date,
                    place_of_service_code=sl.placeOfServiceCode,
                    procedure_code=sl.procedureCode,
                    diagnosis_code_pointer1=sl.diagnosisCodePointer1,
                    amount=sl.amount,
                    quantity=sl.quantity,
                    quantity_type_code=sl.quantityTypeCode,
                ))
        
        # Get payer name (use tradingPartnerServiceId if payer not provided)
        payer_name = request.payer or (request.tradingPartnerServiceId if request.tradingPartnerServiceId else None)
        
        query = ClaimsQuery(
            request_id=request_id_int,
            transaction_type=request.transactionType,
            payer=payer_name,
            responsibility_sequence=request.responsibilitySequence,
            patient_last_name=request.subscriber.lastName,
            patient_first_name=request.subscriber.firstName,
            patient_birth_date=subscriber_dob,
            subscriber_member_id=request.subscriber.memberId,
            billing_provider_npi=provider.npi if provider else None,
            billing_provider_last_name=billing_provider_last_name,
            billing_provider_first_name=billing_provider_first_name,
            patient_paid_amount=request.patientPaidAmount,
            claim_control_number=request.claimControlNumber,
            diagnosis_code=request.diagnosisCode,
            service_lines=service_lines,
        )
        
        # Acquire exclusive access to shared WebDriver instance
        shared_driver = driver_manager.acquire_driver(headless=False)
        
        # Run bot with shared driver
        bot = ClaimsBot(
            base_url=settings.BASE_URL,
            username=settings.USERNAME,
            password=settings.PASSWORD,
            headless=False,  # Show browser for debugging
            artifacts_dir=settings.ARTIFACTS_DIR,
            driver=shared_driver,  # Use shared driver
        )
        
        try:
            result = bot.process_query(query)
            
            return {
                "requestId": request_id,
                "status": result.submission_status or "PROCESSING",
                "claimSubmitted": result.claim_submitted,
                "transactionId": result.transaction_id,
                "claimId": result.claim_id,
                "patientAccountNumber": result.patient_account_number,
                "submissionType": result.submission_type,
                "submissionDate": result.submission_date,
                "datesOfService": result.dates_of_service,
                "patientName": result.patient_name,
                "subscriberId": result.subscriber_id,
                "billingProviderName": result.billing_provider_name,
                "billingProviderNpi": result.billing_provider_npi,
                "billingProviderTaxId": result.billing_provider_tax_id,
                "totalCharges": result.total_charges,
                "errorMessage": result.error_message,
                "rawResponseHtmlPath": result.raw_response_html_path,
            }
        finally:
            bot.close()
            driver_manager.release_driver()  # Release exclusive access
            clear_request_id()
            
    except Exception as e:
        driver_manager.release_driver()  # Release exclusive access on error
        clear_request_id()
        error_msg = str(e)
        logger.error(f"Error processing claims: {e}")
        return {
            "requestId": request_id,
            "status": "FAILED",
            "claimSubmitted": None,
            "transactionId": None,
            "claimId": None,
            "errorMessage": error_msg,
            "rawResponseHtmlPath": None,
        }


def process_eligibility_sync(request: EligibilityRequest, request_id: str) -> dict:
    """Process eligibility check synchronously."""
    try:
        # Generate integer request ID from UUID hash
        request_id_int = int(hashlib.md5(request_id.encode()).hexdigest()[:8], 16) % 1000000000
        set_request_id(request_id_int)
        
        # Convert API request to domain model
        subscriber_dob = datetime.strptime(convert_date_format(request.subscriber.dateOfBirth), "%Y-%m-%d").date()
        
        dos_from = None
        dos_to = None
        if request.encounter:
            dos_from = datetime.strptime(convert_date_format(request.encounter.beginningDateOfService), "%Y-%m-%d").date()
            if request.encounter.endDateOfService:
                dos_to = datetime.strptime(convert_date_format(request.encounter.endDateOfService), "%Y-%m-%d").date()
        
        provider = request.providers[0] if request.providers else None
        
        query = EligibilityRequestModel(
            request_id=request_id_int,
            payer_name=request.payer,
            member_id=request.subscriber.memberId,
            patient_last_name=request.subscriber.lastName,
            patient_first_name=request.subscriber.firstName,
            dob=subscriber_dob,
            dos_from=dos_from or datetime.now().date(),
            dos_to=dos_to,
            service_type_code=request.serviceTypeCode,
            provider_npi=provider.npi if provider else None,
            provider_name=provider.organizationName if provider else None,
        )
        
        # Acquire exclusive access to shared WebDriver instance
        shared_driver = driver_manager.acquire_driver(headless=False)
        
        # Run bot with shared driver
        bot = EligibilityBot(
            base_url=settings.BASE_URL,
            username=settings.USERNAME,
            password=settings.PASSWORD,
            headless=False,  # Show browser for debugging
            artifacts_dir=settings.ARTIFACTS_DIR,
            driver=shared_driver,  # Use shared driver
        )
        
        try:
            result = bot.process_request(query)
            
            return {
                "requestId": request_id,
                "status": "SUCCESS",
                "coverageStatus": result.coverage_status,
                "planName": result.plan_name,
                "planType": result.plan_type,
                "coverageStartDate": str(result.coverage_start_date) if result.coverage_start_date else None,
                "coverageEndDate": str(result.coverage_end_date) if result.coverage_end_date else None,
                "deductibleIndividual": result.deductible_individual,
                "errorMessage": None,
                "rawResponseHtmlPath": result.raw_response_html_path,
            }
        finally:
            bot.close()
            driver_manager.release_driver()  # Release exclusive access
            clear_request_id()
            
    except Exception as e:
        driver_manager.release_driver()  # Release exclusive access on error
        clear_request_id()
        error_msg = str(e)
        logger.error(f"Error processing eligibility: {e}")
        return {
            "requestId": request_id,
            "status": "FAILED",
            "coverageStatus": None,
            "planName": None,
            "planType": None,
            "coverageStartDate": None,
            "coverageEndDate": None,
            "deductibleIndividual": None,
            "errorMessage": error_msg,
            "rawResponseHtmlPath": None,
        }


@app.post("/claim-status", response_model=ClaimStatusResponse)
async def claim_status(
    request: ClaimStatusRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    background_tasks: BackgroundTasks = None
):
    """
    Check claim status.
    
    This endpoint processes claim status inquiries through the Availity portal.
    Uses the same format as input_claim_status.json
    """
    logger.info(f"Received claim status request: {request.request_id}")
    
    # Process synchronously (can be made async with background tasks)
    result = await asyncio.to_thread(process_claim_status_sync, request)
    
    return ClaimStatusResponse(**result)


@app.post("/claims", response_model=ClaimsResponse)
async def claims_submission(
    request: ClaimsRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    background_tasks: BackgroundTasks = None
):
    """
    Submit a claim.
    
    This endpoint submits claims through the Availity portal.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received claims submission request: {request_id}")
    
    # Process synchronously (can be made async with background tasks)
    result = await asyncio.to_thread(process_claims_sync, request, request_id)
    
    return ClaimsResponse(**result)


@app.post("/eligibility", response_model=EligibilityResponse)
async def eligibility_check(
    request: EligibilityRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    background_tasks: BackgroundTasks = None
):
    """
    Check eligibility.
    
    This endpoint checks patient eligibility through the Availity portal.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received eligibility check request: {request_id}")
    
    # Process synchronously (can be made async with background tasks)
    result = await asyncio.to_thread(process_eligibility_sync, request, request_id)
    
    return EligibilityResponse(**result)


@app.on_event("shutdown")
async def shutdown_event():
    """Close shared WebDriver on server shutdown."""
    logger.info("Server shutting down, closing shared WebDriver...")
    driver_manager.close()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Availity Bots API"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Availity Bots API",
        "version": "1.0.0",
        "endpoints": {
            "claim-status": "/claim-status",
            "claims": "/claims",
            "eligibility": "/eligibility",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    # Use 127.0.0.1 for local access, or 0.0.0.0 for all interfaces (then access via localhost:8000)
    uvicorn.run(app, host="127.0.0.1", port=8000)

