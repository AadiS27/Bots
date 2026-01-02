"""Domain models for drug prior authorization workflow using Pydantic."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class DrugPriorAuthQuery(BaseModel):
    """
    Drug Prior Authorization request model.

    This represents the input data needed to perform a drug prior authorization check.
    """

    request_id: int = Field(description="Unique request identifier")
    organization_name: Optional[str] = Field(
        default=None, description="Organization name (if not pre-filled)"
    )
    payer_name: str = Field(description="Insurance payer name")
    
    # Provider information
    provider_npi: str = Field(description="Provider NPI (required)")
    provider_name: Optional[str] = Field(
        default=None, description="Provider name (optional, for matching in search results)"
    )
    provider_address: Optional[str] = Field(
        default=None, description="Provider address (optional, for matching in search results)"
    )
        
    # Routing information (optional - can be determined automatically)
    drug_type: Optional[str] = Field(
        default=None,
        description="Type of drug/service: 'injectable', 'radiation_oncology', or 'other'"
    )
    member_state: Optional[str] = Field(
        default=None,
        description="Member's state code (e.g., 'AZ', 'CT', 'IL', 'PA', 'TX')"
    )
    member_type: Optional[str] = Field(
        default=None,
        description="Member type: 'Commercial', 'Medicare', or 'Exchange'"
    )
    
    # TODO: Add patient and drug information fields after seeing next form steps
    # These will likely include:
    # - member_id: str
    # - patient_last_name: str
    # - patient_first_name: Optional[str]
    # - patient_dob: date
    # - drug_name: str
    # - ndc_code: Optional[str]
    # - dosage: Optional[str]
    # - quantity: Optional[int]
    # - date_of_service: date

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 301,
                "organization_name": "GPT Innovations, Inc.",
                "payer_name": "AETNA (COMMERCIAL & MEDICARE)",
                "provider_npi": "1234567890",
                "provider_name": "1960 PHYSICIAN ASSOCIATE",
                "drug_type": "injectable",
                "member_state": "AZ",
                "member_type": "Commercial",
            }
        }


class DrugPriorAuthResult(BaseModel):
    """
    Drug Prior Authorization result model.

    This represents the parsed output from the drug prior authorization check.
    """

    request_id: int = Field(description="Corresponding request ID")
    routing_path_taken: Optional[str] = Field(
        default=None,
        description="Which path was taken: 'novologix' or 'authorization_request'"
    )
    # TODO: Add result fields after seeing the results page
    # Common fields might include:
    # - prior_auth_status: Optional[str]  # e.g., "APPROVED", "DENIED", "PENDING"
    # - prior_auth_number: Optional[str]
    # - approval_date: Optional[date]
    # - expiration_date: Optional[date]
    # - denial_reason: Optional[str]
    # - required_documentation: Optional[list[str]]
    raw_response_html_path: Optional[str] = Field(
        default=None, description="Path to saved raw HTML response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 301,
                "routing_path_taken": "novologix",
                "prior_auth_status": "APPROVED",
                "prior_auth_number": "PA-12345",
                "raw_response_html_path": "artifacts/drug_prior_auth/response_301_20251105_143022.html",
            }
        }