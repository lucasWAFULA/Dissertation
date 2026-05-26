from pydantic import BaseModel, Field
from typing import Literal, Optional

class CreateIntentRequest(BaseModel):
    amount: int = Field(..., description="Amount in smallest currency unit (e.g., cents)")
    currency: str = Field(default="USD", description="3‑letter ISO currency code")
    provider: Literal["stripe", "paypal", "skrill", "mpesa"] = Field(..., description="Payment provider")
    description: Optional[str] = Field(None, description="Optional description for the payment")

class CreateIntentResponse(BaseModel):
    intent_id: str = Field(..., description="Provider‑specific payment intent identifier")
    client_secret: Optional[str] = Field(None, description="Client secret for Stripe or similar (if needed)")
    next_action_url: Optional[str] = Field(None, description="Redirect URL for PayPal, Skrill, M‑Pesa flows")

class PaymentStatusResponse(BaseModel):
    provider: str
    status: str
    amount: int
    currency: str
    created_at: str
    metadata: Optional[dict] = None
