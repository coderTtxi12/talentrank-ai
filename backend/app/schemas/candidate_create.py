"""Register candidate from recruiter dashboard (subset of legacy loan-style payload)."""

from typing import Literal

from pydantic import BaseModel, Field


class CandidateCreateRequest(BaseModel):
    country_code: Literal["ES", "MX"]
    document_type: Literal["DNI", "CURP", "CC", "CPF"]
    document_number: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2, max_length=160)
    amount_requested: float = Field(ge=0)
    monthly_income: float = Field(ge=0)
