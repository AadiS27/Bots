"""Domain models for appeals workflow using Pydantic."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class AppealsQuery(BaseModel):
    """
    Appeals inquiry request model.

    This represents the input data needed to search for appeals.
    """

    request_id: int = Field(description="Unique request identifier")
    search_by: str = Field(description="Search criteria type (e.g., 'Claim Number', 'Member ID', 'Patient Name')")
    search_term: str = Field(description="Search term value")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 301,
                "search_by": "Claim Number",
                "search_term": "45646546465",
            }
        }


class AppealsResult(BaseModel):
    """
    Appeals inquiry result model.

    This represents the parsed output from the appeals search.
    """

    request_id: int = Field(description="Corresponding request ID")
    appeals_found: int = Field(default=0, description="Number of appeals found")
    appeals: list[dict] = Field(default_factory=list, description="List of appeals with their details")
    raw_response_html_path: Optional[str] = Field(default=None, description="Path to saved raw HTML response")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 301,
                "appeals_found": 2,
                "appeals": [
                    {
                        "appeal_id": "APL-12345",
                        "claim_number": "45646546465",
                        "status": "Pending",
                        "submitted_date": "2025-10-15",
                    }
                ],
                "raw_response_html_path": "artifacts/appeals/response_301_20251020_143022.html",
            }
        }

