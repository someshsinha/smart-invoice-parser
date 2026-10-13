from typing import Any, List, Optional
from pydantic import BaseModel, Field


class FieldConfidence(BaseModel):
    vendor: float = Field(default=0.0, ge=0.0, le=1.0)
    invoice_number: float = Field(default=0.0, ge=0.0, le=1.0)
    invoice_date: float = Field(default=0.0, ge=0.0, le=1.0)
    due_date: float = Field(default=0.0, ge=0.0, le=1.0)
    currency: float = Field(default=0.0, ge=0.0, le=1.0)
    subtotal: float = Field(default=0.0, ge=0.0, le=1.0)
    tax: float = Field(default=0.0, ge=0.0, le=1.0)
    total: float = Field(default=0.0, ge=0.0, le=1.0)


class InvoiceExtractionResponse(BaseModel):
    vendor: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    confidence: FieldConfidence
    warnings: List[str] = Field(default_factory=list)
    debug: Optional[Any] = Field(default=None)


class HealthResponse(BaseModel):
    status: str = "ok"
