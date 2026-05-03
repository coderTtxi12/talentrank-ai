"""Request body for **POST** create-candidate from the recruiter dashboard.

Carries a minimal identity block plus legacy-style financial placeholders
(`amount_requested`, `monthly_income`) kept for UI parity with older flows;
screening-specific fields are filled later via chat or other endpoints.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CandidateCreateRequest(BaseModel):
    """Validated payload to insert a new ``Candidate`` row from the dashboard."""

    country_code: Literal["ES", "MX"]
    document_type: Literal["DNI", "CURP", "CC", "CPF"]
    document_number: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2, max_length=160)
    amount_requested: float = Field(ge=0)
    monthly_income: float = Field(ge=0)
