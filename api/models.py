"""API request/response models."""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class Provider(BaseModel):
    """Provider information."""
    npi: str = Field(description="Provider NPI")
    organizationName: Optional[str] = Field(default=None, description="Organization name")
    providerType: str = Field(description="Provider type (e.g., 'BillingProvider')")


class Encounter(BaseModel):
    """Encounter/date of service information."""
    beginningDateOfService: str = Field(description="Beginning date of service (YYYYMMDD)")
    endDateOfService: Optional[str] = Field(default=None, description="End date of service (YYYYMMDD)")


class Subscriber(BaseModel):
    """Subscriber/patient information."""
    dateOfBirth: str = Field(description="Date of birth (YYYYMMDD)")
    firstName: str = Field(description="First name")
    lastName: str = Field(description="Last name")
    memberId: str = Field(description="Member ID")


# ========== Claim Status API Models ==========

class ClaimStatusRequest(BaseModel):
    """Claim status check API request - matches input_claim_status.json format."""
    request_id: int = Field(description="Unique request identifier")
    payer_name: str = Field(description="Insurance payer name")
    payer_claim_id: Optional[str] = Field(default=None, description="Payer-assigned claim ID")
    provider_claim_id: Optional[str] = Field(default=None, description="Provider-assigned claim ID")
    member_id: Optional[str] = Field(default=None, description="Patient member ID with the payer")
    patient_last_name: Optional[str] = Field(default=None, description="Patient last name")
    patient_first_name: Optional[str] = Field(default=None, description="Patient first name")
    patient_dob: Optional[str] = Field(default=None, description="Patient date of birth (YYYY-MM-DD)")
    subscriber_last_name: Optional[str] = Field(default=None, description="Subscriber last name")
    subscriber_first_name: Optional[str] = Field(default=None, description="Subscriber first name")
    subscriber_same_as_patient: bool = Field(default=True, description="Whether subscriber is same as patient")
    provider_npi: Optional[str] = Field(default=None, description="Provider NPI")
    dos_from: str = Field(description="Date of service from (YYYY-MM-DD)")
    dos_to: Optional[str] = Field(default=None, description="Date of service to (YYYY-MM-DD), if range")
    claim_amount: Optional[float] = Field(default=None, description="Claim amount")


class ClaimStatusResponse(BaseModel):
    """Claim status check API response - matches output_claim_status.json format."""
    request_id: int = Field(description="Request ID")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID")
    high_level_status: Optional[str] = Field(default=None, description="High level status (e.g., 'PAID', 'DENIED', 'PENDING')")
    status_code: Optional[str] = Field(default=None, description="Status code")
    finalized_date: Optional[str] = Field(default=None, description="Finalized date (YYYY-MM-DD)")
    service_dates: Optional[str] = Field(default=None, description="Service dates")
    claim_number: Optional[str] = Field(default=None, description="Claim number")
    member_name: Optional[str] = Field(default=None, description="Member name")
    member_id: Optional[str] = Field(default=None, description="Member ID")
    billed_amount: Optional[float] = Field(default=None, description="Billed amount")
    paid_amount: Optional[float] = Field(default=None, description="Paid amount")
    check_or_eft_number: Optional[str] = Field(default=None, description="Check or EFT number")
    payment_date: Optional[str] = Field(default=None, description="Payment date (YYYY-MM-DD)")
    reason_codes: list[dict] = Field(default_factory=list, description="List of reason codes with code_type, code, and description")


# ========== Claims Submission API Models ==========

class ServiceLineRequest(BaseModel):
    """Service line for claims submission."""
    fromDate: str = Field(description="Service date (YYYY-MM-DD)")
    placeOfServiceCode: Optional[str] = Field(default=None, description="Place of service code")
    procedureCode: Optional[str] = Field(default=None, description="Procedure code")
    diagnosisCodePointer1: Optional[str] = Field(default=None, description="Diagnosis code pointer")
    amount: Optional[str] = Field(default=None, description="Amount")
    quantity: Optional[str] = Field(default=None, description="Quantity")
    quantityTypeCode: Optional[str] = Field(default="UN - Unit", description="Quantity type code")


class ClaimsRequest(BaseModel):
    """Claims submission API request."""
    tradingPartnerServiceId: Optional[str] = Field(default=None, description="Trading partner service ID")
    transactionType: str = Field(description="Transaction type (e.g., 'Professional Claim')")
    payer: Optional[str] = Field(default=None, description="Payer name")
    responsibilitySequence: str = Field(default="Primary", description="Responsibility sequence")
    subscriber: Subscriber = Field(description="Subscriber information")
    providers: List[Provider] = Field(description="List of providers")
    encounter: Optional[Encounter] = Field(default=None, description="Encounter information")
    serviceLines: Optional[List[ServiceLineRequest]] = Field(default=None, description="Service lines")
    patientPaidAmount: Optional[str] = Field(default=None, description="Patient paid amount")
    claimControlNumber: Optional[str] = Field(default=None, description="Claim control number")
    diagnosisCode: Optional[str] = Field(default=None, description="Primary diagnosis code")
    # Additional fields can be added as needed


class ClaimsResponse(BaseModel):
    """Claims submission API response."""
    requestId: str = Field(description="Request ID")
    status: str = Field(description="Status (SUBMITTED, FAILED, PROCESSING)")
    claimSubmitted: Optional[str] = Field(default=None, description="Claim submitted message")
    transactionId: Optional[str] = Field(default=None, description="Transaction ID")
    claimId: Optional[str] = Field(default=None, description="Claim ID")
    patientAccountNumber: Optional[str] = Field(default=None, description="Patient account number")
    submissionType: Optional[str] = Field(default=None, description="Submission type")
    submissionDate: Optional[str] = Field(default=None, description="Submission date")
    datesOfService: Optional[str] = Field(default=None, description="Dates of service")
    patientName: Optional[str] = Field(default=None, description="Patient name")
    subscriberId: Optional[str] = Field(default=None, description="Subscriber ID")
    billingProviderName: Optional[str] = Field(default=None, description="Billing provider name")
    billingProviderNpi: Optional[str] = Field(default=None, description="Billing provider NPI")
    billingProviderTaxId: Optional[str] = Field(default=None, description="Billing provider tax ID")
    totalCharges: Optional[str] = Field(default=None, description="Total charges")
    errorMessage: Optional[str] = Field(default=None, description="Error message if failed")
    rawResponseHtmlPath: Optional[str] = Field(default=None, description="Path to raw HTML response")


# ========== Eligibility API Models ==========

class EligibilityRequest(BaseModel):
    """Eligibility check API request."""
    tradingPartnerServiceId: Optional[str] = Field(default=None, description="Trading partner service ID")
    payer: str = Field(description="Payer name")
    subscriber: Subscriber = Field(description="Subscriber information")
    encounter: Optional[Encounter] = Field(default=None, description="Encounter information")
    serviceTypeCode: Optional[str] = Field(default=None, description="Service type code")
    providers: Optional[List[Provider]] = Field(default=None, description="List of providers")


class EligibilityResponse(BaseModel):
    """Eligibility check API response."""
    requestId: str = Field(description="Request ID")
    status: str = Field(description="Status (SUCCESS, FAILED, PROCESSING)")
    coverageStatus: Optional[str] = Field(default=None, description="Coverage status")
    planName: Optional[str] = Field(default=None, description="Plan name")
    planType: Optional[str] = Field(default=None, description="Plan type")
    coverageStartDate: Optional[str] = Field(default=None, description="Coverage start date")
    coverageEndDate: Optional[str] = Field(default=None, description="Coverage end date")
    deductibleIndividual: Optional[float] = Field(default=None, description="Individual deductible")
    errorMessage: Optional[str] = Field(default=None, description="Error message if failed")
    rawResponseHtmlPath: Optional[str] = Field(default=None, description="Path to raw HTML response")


# ========== Generic Response ==========

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Error details")

