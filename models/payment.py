from datetime import datetime
from . import db, MONEY


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    amount = db.Column(MONEY, nullable=False)
    payment_status = db.Column(db.String(20), nullable=False)  # SUCCESS / FAILED
    transaction_id = db.Column(db.String(40), unique=True, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.now)
