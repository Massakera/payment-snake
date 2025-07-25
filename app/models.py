from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime

class PaymentRequest(BaseModel):
    correlationId: str = Field(..., description="Unique payment identifier")
    amount: Decimal = Field(..., description="Payment amount")

class PaymentProcessorRequest(BaseModel):
    correlationId: str
    amount: Decimal
    requestedAt: str

class PaymentProcessorResponse(BaseModel):
    message: str

class HealthCheckResponse(BaseModel):
    failing: bool
    minResponseTime: int

class PaymentSummary(BaseModel):
    totalRequests: int
    totalAmount: Decimal

class PaymentSummaryResponse(BaseModel):
    default: PaymentSummary
    fallback: PaymentSummary

class AdminPaymentSummary(BaseModel):
    totalRequests: int
    totalAmount: Decimal
    totalFee: Decimal
    feePerTransaction: Decimal 