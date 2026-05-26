from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from typing import Optional

from api.auth.dependencies import get_current_user, UserContext
from . import schemas, service, models
from api.auth.quota import SessionLocal, engine

# Ensure payment table exists (create if missing)
models.Base.metadata.create_all(bind=engine)

router = APIRouter()

@router.post("/create-intent", response_model=schemas.CreateIntentResponse)
async def create_intent(
    payload: schemas.CreateIntentRequest,
    user: UserContext = Depends(get_current_user),
) -> schemas.CreateIntentResponse:
    # Create payment intent via selected provider
    try:
        result = service.create_intent(
            user_id=user.uid,
            amount=payload.amount,
            currency=payload.currency,
            provider=payload.provider,
            description=payload.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Persist payment record
    db = SessionLocal()
    try:
        payment = models.Payment(
            user_id=user.uid,
            provider=payload.provider,
            payment_intent_id=result["intent_id"],
            status="created",
            amount=payload.amount,
            currency=payload.currency.upper(),
            metadata={"description": payload.description or ""},
        )
        db.add(payment)
        db.commit()
    finally:
        SessionLocal.remove()

    return schemas.CreateIntentResponse(
        intent_id=result["intent_id"],
        client_secret=result.get("client_secret"),
        next_action_url=result.get("next_action_url"),
    )

@router.get("/status/{intent_id}", response_model=schemas.PaymentStatusResponse)
async def get_status(
    intent_id: str,
    provider: str,
    user: UserContext = Depends(get_current_user),
) -> schemas.PaymentStatusResponse:
    # Verify the payment belongs to the user
    db = SessionLocal()
    try:
        payment = (
            db.query(models.Payment)
            .filter(models.Payment.payment_intent_id == intent_id, models.Payment.user_id == user.uid)
            .first()
        )
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
    finally:
        SessionLocal.remove()

    # Retrieve current status from provider
    status_data = service.retrieve_intent(intent_id=intent_id, provider=provider)
    # Update DB status if changed
    db = SessionLocal()
    try:
        if payment.status != status_data.get("status", payment.status):
            payment.status = status_data["status"]
            db.add(payment)
            db.commit()
    finally:
        SessionLocal.remove()

    return schemas.PaymentStatusResponse(
        provider=provider,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        created_at=payment.created_at.isoformat() if payment.created_at else "",
        metadata=payment.metadata,
    )

@router.post("/webhook/{provider}")
async def webhook(
    provider: str,
    request: Request,
) -> Response:
    raw_body = await request.body()
    sig_header: Optional[str] = request.headers.get("Stripe-Signature") if provider == "stripe" else None
    try:
        event = service.process_webhook(provider, raw_body, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process event: for Stripe we expect a "payment_intent.succeeded" or similar
    if provider == "stripe":
        obj = event.get("data", {}).get("object", {})
        intent_id = obj.get("id")
        status = obj.get("status")
    else:
        # For PayPal, Skrill, Flutterwave the payload structure can vary; we attempt generic keys
        intent_id = event.get("id") or event.get("transaction_id")
        status = event.get("status")

    if not intent_id:
        raise HTTPException(status_code=400, detail="Unable to extract intent ID from webhook payload")

    # Update payment record
    db = SessionLocal()
    try:
        payment = db.query(models.Payment).filter(models.Payment.payment_intent_id == intent_id).first()
        if payment:
            payment.status = status or payment.status
            db.add(payment)
            db.commit()
    finally:
        SessionLocal.remove()

    return JSONResponse(content={"received": True}, status_code=status.HTTP_200_OK)
