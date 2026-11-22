from datetime import datetime
from . import db, MONEY

# Order lifecycle (admin moves it forward one step at a time)
STATUSES = ["PLACED", "CONFIRMED", "SHIPPED", "DELIVERED"]
PAYMENT_METHODS = ("ONLINE", "COD")
ORDER_REQUEST_TYPES = ("CANCEL", "RETURN", "EXCHANGE")
ORDER_REQUEST_STATUSES = ("PENDING", "APPROVED", "REJECTED")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.now)
    total_amount = db.Column(MONEY, nullable=False)
    order_status = db.Column(db.String(20), nullable=False, default="PLACED")
    payment_status = db.Column(db.String(20), nullable=False, default="PENDING")  # PENDING / SUCCESS / FAILED
    payment_method = db.Column(db.String(20), nullable=False, default="ONLINE")
    delivery_address = db.Column(db.Text, nullable=False)

    user = db.relationship("User", backref="orders")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="order", order_by="Payment.id")
    requests = db.relationship("OrderRequest", backref="order", cascade="all, delete-orphan",
                               order_by="OrderRequest.id")

    @property
    def display_id(self):
        return f"BN{self.id:05d}"

    @property
    def status_index(self):
        return STATUSES.index(self.order_status) if self.order_status in STATUSES else -1


class OrderRequest(db.Model):
    __tablename__ = "order_requests"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    request_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    requested_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    resolved_at = db.Column(db.DateTime)


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(MONEY, nullable=False)  # price at the time of purchase

    book = db.relationship("Book")
