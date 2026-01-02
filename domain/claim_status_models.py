"""Domain models for claim status workflow using Pydantic."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ClaimStatusQuery(BaseModel):
    """
    Claim status inquiry request model.

    This represents the input data needed to perform a claim status check.
    """

    request_id: int = Field(description="Unique request identifier")
    payer_name: str = Field(description="Insurance payer name")
    payer_claim_id: Optional[str] = Field(default=None, description="Payer-assigned claim ID")
    provider_claim_id: Optional[str] = Field(default=None, description="Provider-assigned claim ID")
    member_id: Optional[str] = Field(default=None, description="Patient member ID with the payer")
    # Patient information (may be required by form)
    patient_last_name: Optional[str] = Field(default=None, description="Patient last name")
    patient_first_name: Optional[str] = Field(default=None, description="Patient first name")
    patient_dob: Optional[date] = Field(default=None, description="Patient date of birth")
    # Subscriber information (may be required by form)
    subscriber_last_name: Optional[str] = Field(default=None, description="Subscriber last name")
    subscriber_first_name: Optional[str] = Field(default=None, description="Subscriber first name")
    subscriber_same_as_patient: bool = Field(default=True, description="Whether subscriber is same as patient")
    provider_npi: Optional[str] = Field(default=None, description="Provider NPI")
    dos_from: date = Field(description="Date of service (from)")
    dos_to: Optional[date] = Field(default=None, description="Date of service (to), if range")
    claim_amount: Optional[float] = Field(default=None, description="Claim amount")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 201,
                "payer_name": "CIGNA HEALTHCARE",
                "payer_claim_id": "PAYER-CLM-123456",
                "provider_claim_id": None,
                "member_id": "XY6546549875654",
                "patient_last_name": "Aadu",
                "patient_first_name": "Suagasdk",
                "patient_dob": "2005-12-01",
                "subscriber_last_name": "asdasd",
                "subscriber_first_name": "asdasdasd",
                "subscriber_same_as_patient": False,
                "dos_from": "2025-10-20",
                "dos_to": None,
                "claim_amount": 125.00,
            }
        }


class ClaimStatusReason(BaseModel):
    """Individual reason code from claim status result."""

    code_type: str = Field(description="Code type (e.g., 'CARC', 'RARC', 'LOCAL')")
    code: str = Field(description="Reason code")
    description: Optional[str] = Field(default=None, description="Reason description")

    class Config:
        json_schema_extra = {
            "example": {
                "code_type": "CARC",
                "code": "96",
                "description": "Non-covered charge(s)",
            }
        }


class ClaimStatusResult(BaseModel):
    """
    Claim status inquiry result model.

    This represents the parsed output from the claim status check.
    """

    request_id: int = Field(description="Corresponding request ID")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID from results")
    high_level_status: Optional[str] = Field(
        default=None, description="High-level status (e.g., 'RECEIVED', 'IN_PROCESS', 'PAID', 'DENIED')"
    )
    status_code: Optional[str] = Field(default=None, description="Detailed status code")
    finalized_date: Optional[date] = Field(default=None, description="Finalized date")
    service_dates: Optional[str] = Field(default=None, description="Service dates (from-to or single date)")
    claim_number: Optional[str] = Field(default=None, description="Claim number")
    member_name: Optional[str] = Field(default=None, description="Member name")
    member_id: Optional[str] = Field(default=None, description="Member ID")
    billed_amount: Optional[float] = Field(default=None, description="Billed amount")
    paid_amount: Optional[float] = Field(default=None, description="Paid amount")
    check_or_eft_number: Optional[str] = Field(default=None, description="Check or EFT number")
    payment_date: Optional[date] = Field(default=None, description="Payment date")
    reason_codes: list[ClaimStatusReason] = Field(default_factory=list, description="List of reason codes")
    raw_response_html_path: Optional[str] = Field(default=None, description="Path to saved raw HTML response")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 201,
                "high_level_status": "PAID",
                "status_code": "1",
                "status_date": "2025-10-25",
                "paid_amount": 100.00,
                "allowed_amount": 125.00,
                "check_or_eft_number": "CHK123456",
                "payment_date": "2025-10-30",
                "reason_codes": [
                    {
                        "code_type": "CARC",
                        "code": "96",
                        "description": "Non-covered charge(s)",
                    }
                ],
                "raw_response_html_path": "artifacts/claim_status/response_201_20251020_143022.html",
            }
        }

