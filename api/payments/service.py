import os
import json
import logging
from typing import Dict, Any

import httpx

# Stripe SDK import – will be optional if not installed yet
try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None

logger = logging.getLogger(__name__)

# ---------- Helper utilities ----------

def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None:
        if default is not None:
            return default
        raise RuntimeError(f"Environment variable {name} is required for payment integration")
    return value

# ---------- Provider: Stripe ----------

def _init_stripe():
    if stripe is None:
        raise RuntimeError("stripe package not installed")
    stripe.api_key = _get_env("STRIPE_SECRET_KEY")

def create_stripe_intent(user_id: str, amount: int, currency: str, description: str | None = None) -> Dict[str, Any]:
    _init_stripe()
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency.lower(),
        metadata={"user_id": user_id, "description": description or ""},
        description=description,
    )
    return {"intent_id": intent.id, "client_secret": intent.client_secret}

def retrieve_stripe_intent(intent_id: str) -> Dict[str, Any]:
    _init_stripe()
    intent = stripe.PaymentIntent.retrieve(intent_id)
    return {"status": intent.status, "amount": intent.amount, "currency": intent.currency}

def verify_stripe_webhook(request_body: bytes, sig_header: str) -> Dict[str, Any]:
    _init_stripe()
    endpoint_secret = _get_env("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(request_body, sig_header, endpoint_secret)
    except Exception as e:  # pragma: no cover
        logger.error("Stripe webhook signature verification failed: %s", e)
        raise
    return event

# ---------- Provider: PayPal (sandbox) ----------

def _paypal_access_token() -> str:
    client_id = _get_env("PAYPAL_CLIENT_ID")
    client_secret = _get_env("PAYPAL_CLIENT_SECRET")
    auth = httpx.BasicAuth(client_id, client_secret)
    resp = httpx.post(
        "https://api.sandbox.paypal.com/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=auth,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def create_paypal_order(user_id: str, amount: int, currency: str, description: str | None = None) -> Dict[str, Any]:
    token = _paypal_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": user_id,
                "amount": {"currency_code": currency.upper(), "value": f"{amount / 100:.2f}"},
                "description": description or "Payment",
            }
        ],
        "application_context": {"return_url": "https://api.marketpulse.services/payments/webhook/paypal", "cancel_url": "https://api.marketpulse.services/payments/cancel"},
    }
    resp = httpx.post("https://api.sandbox.paypal.com/v2/checkout/orders", json=order_payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # Extract approval link for redirect
    approval_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
    return {"intent_id": data["id"], "next_action_url": approval_url}

def capture_paypal_order(order_id: str) -> Dict[str, Any]:
    token = _paypal_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.post(f"https://api.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    status = data["status"].lower()
    return {"status": status}

# ---------- Provider: Skrill (placeholder) ----------
def create_skrill_payment(user_id: str, amount: int, currency: str, description: str | None = None) -> Dict[str, Any]:
    # Skrill integration typically uses form POST redirects. Here we return a mock URL.
    # In production you would generate a signed URL with your merchant credentials.
    mock_url = f"https://pay.skrill.com/?pay_to_email=merchant@example.com&amount={amount/100:.2f}&currency={currency.upper()}&detail={description or ''}"
    return {"intent_id": f"skrill-{user_id}-{amount}", "next_action_url": mock_url}

# ---------- Provider: M-Pesa via Flutterwave ----------
def create_mpesa_payment(user_id: str, amount: int, currency: str, description: str | None = None) -> Dict[str, Any]:
    public_key = _get_env("FLUTTERWAVE_PUBLIC_KEY")
    secret_key = _get_env("FLUTTERWAVE_SECRET_KEY")
    headers = {"Authorization": f"Bearer {secret_key}", "Content-Type": "application/json"}
    payload = {
        "tx_ref": f"mpesa-{user_id}-{amount}",
        "amount": f"{amount/100:.2f}",
        "currency": currency.upper(),
        "redirect_url": "https://api.marketpulse.services/payments/webhook/mpesa",
        "payment_options": "mobile_money",
        "mobile_money": {"phone": "2547XXXXXXXX", "carrier": "MTN"},
        "customer": {"email": f"{user_id}@example.com", "phonenumber": "2547XXXXXXXX", "name": "User"},
        "customizations": {"title": "MarketPulse Payment", "description": description or ""},
    }
    resp = httpx.post("https://api.flutterwave.com/v3/payments", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError("Flutterwave payment initiation failed")
    link = data["data"]["link"]
    return {"intent_id": data["data"]["tx_ref"], "next_action_url": link}

# ---------- Unified service functions ----------

def create_intent(user_id: str, amount: int, currency: str, provider: str, description: str | None = None) -> Dict[str, Any]:
    if provider == "stripe":
        return create_stripe_intent(user_id, amount, currency, description)
    if provider == "paypal":
        return create_paypal_order(user_id, amount, currency, description)
    if provider == "skrill":
        return create_skrill_payment(user_id, amount, currency, description)
    if provider == "mpesa":
        return create_mpesa_payment(user_id, amount, currency, description)
    raise ValueError(f"Unsupported payment provider: {provider}")

def retrieve_intent(intent_id: str, provider: str) -> Dict[str, Any]:
    if provider == "stripe":
        return retrieve_stripe_intent(intent_id)
    if provider == "paypal":
        return capture_paypal_order(intent_id)
    # Skrill & M-Pesa status checks would normally hit their APIs; return placeholder
    return {"status": "unknown", "provider": provider, "intent_id": intent_id}

def process_webhook(provider: str, payload: bytes, sig_header: str | None = None) -> Dict[str, Any]:
    if provider == "stripe":
        if sig_header is None:
            raise ValueError("Stripe webhook requires signature header")
        return verify_stripe_webhook(payload, sig_header)
    # PayPal, Skrill, Flutterwave webhooks can be parsed from payload JSON directly
    data = json.loads(payload)
    return data
