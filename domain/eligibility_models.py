"""Domain models for eligibility workflow using Pydantic."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    """
    Eligibility check request model.

    This represents the input data needed to perform an eligibility check.
    """

    request_id: int = Field(description="Unique request identifier")
    payer_name: str = Field(description="Insurance payer name")
    member_id: str = Field(description="Patient member ID with the payer")
    patient_last_name: str = Field(description="Patient last name")
    patient_first_name: Optional[str] = Field(default=None, description="Patient first name")
    dob: date = Field(description="Patient date of birth")
    dos_from: date = Field(description="Date of service (from)")
    dos_to: Optional[date] = Field(default=None, description="Date of service (to), if range")
    service_type_code: Optional[str] = Field(default=None, description="Service type code (e.g., '30' for Health Benefit Plan Coverage)")
    provider_name: Optional[str] = Field(default=None, description="Provider name (e.g., '1960 PHYSICIAN ASSOCIATE')")
    provider_npi: Optional[str] = Field(default=None, description="Provider NPI number")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 101,
                "payer_name": "CIGNA HEALTHCARE",
                "member_id": "AB123456789",
                "patient_last_name": "DOE",
                "patient_first_name": "JOHN",
                "dob": "1987-06-15",
                "dos_from": "2025-11-05",
                "dos_to": None,
                "service_type_code": "30",
                "provider_npi": "1234567890",
            }
        }


class EligibilityBenefitLine(BaseModel):
    """Individual benefit line from eligibility result."""

    benefit_category: str = Field(description="Benefit category (e.g., 'Medical', 'Pharmacy', 'Dental')")
    service_type_code: Optional[str] = Field(default=None, description="Service type code")
    network_tier: Optional[str] = Field(default=None, description="Network tier (e.g., 'In-Network', 'Out-of-Network')")
    copay_amount: Optional[float] = Field(default=None, description="Copay amount")
    coinsurance_percent: Optional[float] = Field(default=None, description="Coinsurance percentage")
    deductible_amount: Optional[float] = Field(default=None, description="Deductible amount")
    max_benefit_amount: Optional[float] = Field(default=None, description="Maximum benefit amount")
    notes: Optional[str] = Field(default=None, description="Additional notes or details")

    class Config:
        json_schema_extra = {
            "example": {
                "benefit_category": "Primary Care Office Visit",
                "service_type_code": "30",
                "network_tier": "In-Network",
                "copay_amount": 25.00,
                "coinsurance_percent": None,
                "deductible_amount": None,
                "max_benefit_amount": None,
                "notes": "Copay waived if deductible not met",
            }
        }


class EligibilityResult(BaseModel):
    """
    Eligibility check result model.

    This represents the parsed output from the eligibility check.
    """

    request_id: int = Field(description="Corresponding request ID")
    coverage_status: Optional[str] = Field(default=None, description="Coverage status (e.g., 'Active', 'Inactive')")
    plan_name: Optional[str] = Field(default=None, description="Insurance plan name")
    plan_type: Optional[str] = Field(default=None, description="Plan type (e.g., 'HMO', 'PPO', 'EPO')")
    coverage_start_date: Optional[date] = Field(default=None, description="Coverage start date")
    coverage_end_date: Optional[date] = Field(default=None, description="Coverage end date")
    deductible_individual: Optional[float] = Field(default=None, description="Individual deductible amount")
    deductible_remaining_individual: Optional[float] = Field(default=None, description="Individual deductible remaining")
    oop_max_individual: Optional[float] = Field(default=None, description="Individual out-of-pocket maximum")
    oop_max_family: Optional[float] = Field(default=None, description="Family out-of-pocket maximum")
    benefit_lines: list[EligibilityBenefitLine] = Field(default_factory=list, description="Detailed benefit lines")
    raw_response_html_path: Optional[str] = Field(default=None, description="Path to saved raw HTML response")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 101,
                "coverage_status": "Active",
                "plan_name": "CIGNA OPEN ACCESS PLUS",
                "plan_type": "PPO",
                "coverage_start_date": "2025-01-01",
                "coverage_end_date": "2025-12-31",
                "deductible_individual": 1500.00,
                "deductible_remaining_individual": 800.00,
                "oop_max_individual": 5000.00,
                "oop_max_family": 10000.00,
                "benefit_lines": [
                    {
                        "benefit_category": "Primary Care Office Visit",
                        "service_type_code": "30",
                        "network_tier": "In-Network",
                        "copay_amount": 25.00,
                        "coinsurance_percent": None,
                        "deductible_amount": None,
                        "max_benefit_amount": None,
                        "notes": None,
                    }
                ],
                "raw_response_html_path": "artifacts/response_101_20251105_143022.html",
            }
        }

