from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True, comment="Firebase UID of payer")
    provider = Column(String, nullable=False)
    payment_intent_id = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="created")
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata = Column(JSON, nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "payment_intent_id": self.payment_intent_id,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }
