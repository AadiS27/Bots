"""Domain models for claims submission workflow using Pydantic."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ServiceLine(BaseModel):
    """Service line model for claims submission."""

    from_date: Optional[date] = Field(default=None, description="Service line from date")
    place_of_service_code: Optional[str] = Field(default=None, description="Service line place of service code")
    procedure_code: Optional[str] = Field(default=None, description="Service line procedure code")
    diagnosis_code_pointer1: Optional[str] = Field(default=None, description="Service line diagnosis code pointer 1")
    amount: Optional[str] = Field(default=None, description="Service line amount")
    quantity: Optional[str] = Field(default=None, description="Service line quantity")
    quantity_type_code: Optional[str] = Field(default="UN - Unit", description="Service line quantity type code")


class ClaimsQuery(BaseModel):
    """
    Claims submission request model.

    This represents the input data needed to submit a claim.
    """

    request_id: int = Field(description="Unique request identifier")
    transaction_type: str = Field(description="Claim transaction type (e.g., 'Professional Claim', 'Institutional')")
    payer: Optional[str] = Field(default=None, description="Payer name")
    responsibility_sequence: str = Field(default="Primary", description="Responsibility sequence (e.g., 'Primary', 'Secondary')")
    # Patient information
    patient_last_name: Optional[str] = Field(default=None, description="Patient last name")
    patient_first_name: Optional[str] = Field(default=None, description="Patient first name")
    patient_birth_date: Optional[date] = Field(default=None, description="Patient date of birth")
    patient_gender_code: Optional[str] = Field(default=None, description="Patient gender code")
    patient_subscriber_relationship_code: Optional[str] = Field(default="Self", description="Patient subscriber relationship code")
    # Subscriber information
    subscriber_member_id: Optional[str] = Field(default=None, description="Subscriber member ID")
    subscriber_group_number: Optional[str] = Field(default=None, description="Subscriber group number")
    # Patient address
    patient_address_line1: Optional[str] = Field(default=None, description="Patient address line 1")
    patient_country_code: Optional[str] = Field(default="United States", description="Patient country code")
    patient_city: Optional[str] = Field(default=None, description="Patient city")
    patient_state_code: Optional[str] = Field(default=None, description="Patient state code")
    patient_zip_code: Optional[str] = Field(default=None, description="Patient zip code")
    # Claim information
    patient_paid_amount: Optional[str] = Field(default=None, description="Patient paid amount")
    benefits_assignment_certification: Optional[str] = Field(default=None, description="Benefits assignment certification")
    claim_control_number: Optional[str] = Field(default=None, description="Claim control number")
    place_of_service_code: Optional[str] = Field(default=None, description="Place of service code")
    frequency_type_code: Optional[str] = Field(default=None, description="Frequency type code")
    provider_accept_assignment_code: Optional[str] = Field(default=None, description="Provider accept assignment code")
    information_release_code: Optional[str] = Field(default=None, description="Information release code")
    provider_signature_on_file: Optional[str] = Field(default=None, description="Provider signature on file")
    payer_claim_filing_indicator_code: Optional[str] = Field(default="CI - Commercial Insurance Co.", description="Payer claim filing indicator code")
    medical_record_number: Optional[str] = Field(default=None, description="Medical record number")
    # Billing provider information
    billing_provider_last_name: Optional[str] = Field(default=None, description="Billing provider last name")
    billing_provider_first_name: Optional[str] = Field(default=None, description="Billing provider first name")
    billing_provider_npi: Optional[str] = Field(default=None, description="Billing provider NPI (10 digits)")
    billing_provider_tax_id_ein: Optional[str] = Field(default=None, description="Billing provider Tax ID EIN (9 digits)")
    billing_provider_tax_id_ssn: Optional[str] = Field(default=None, description="Billing provider Tax ID SSN (9 digits)")
    billing_provider_specialty_code: Optional[str] = Field(default=None, description="Billing provider specialty code")
    billing_provider_address_line1: Optional[str] = Field(default=None, description="Billing provider address line 1")
    billing_provider_country_code: Optional[str] = Field(default="United States", description="Billing provider country code")
    billing_provider_city: Optional[str] = Field(default=None, description="Billing provider city")
    billing_provider_state_code: Optional[str] = Field(default=None, description="Billing provider state code")
    billing_provider_zip_code: Optional[str] = Field(default=None, description="Billing provider zip code")
    # Diagnosis information
    diagnosis_code: Optional[str] = Field(default=None, description="Primary diagnosis code")
    # Service lines (list of service lines)
    service_lines: list[ServiceLine] = Field(default_factory=list, description="List of service lines")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 401,
                "transaction_type": "Professional Claim",
                "payer": "AETNA (COMMERCIAL & MEDICARE)",
                "responsibility_sequence": "Primary",
                "patient_last_name": "Smith",
            }
        }


class ClaimsResult(BaseModel):
    """
    Claims submission result model.

    This represents the parsed output from the claim submission.
    """

    request_id: int = Field(description="Corresponding request ID")
    submission_status: Optional[str] = Field(default=None, description="Submission status (e.g., 'SUBMITTED', 'PENDING', 'FAILED')")
    claim_id: Optional[str] = Field(default=None, description="Claim ID or confirmation number")
    error_message: Optional[str] = Field(default=None, description="Error message if submission failed")
    raw_response_html_path: Optional[str] = Field(default=None, description="Path to saved raw HTML response")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 401,
                "submission_status": "SUBMITTED",
                "claim_id": "CLM-123456",
                "error_message": None,
                "raw_response_html_path": "artifacts/claims/response_401_20251020_143022.html",
            }
        }

