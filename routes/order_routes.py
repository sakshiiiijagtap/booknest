import re
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, abort
from models import (db, CartItem, Order, OrderItem, OrderRequest, STATUSES,
                    PAYMENT_METHODS, ORDER_REQUEST_TYPES)
from routes.helpers import login_required, get_current_user

order_bp = Blueprint("orders", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@order_bp.route("/checkout")
@login_required
def checkout():
    user = get_current_user()
    items = CartItem.query.filter_by(user_id=user.id).all()
    total = sum(i.book.price * i.quantity for i in items)
    return render_template("checkout.html", items=items, total=total)


@order_bp.route("/api/checkout", methods=["POST"])
@login_required
def place_order():
    """Creates an order with payment PENDING. Stock is NOT reduced until payment succeeds."""
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    f = {k: str(data.get(k, "")).strip() for k in ("name", "email", "phone", "address", "city", "pin")}

    errors = {}
    if len(f["name"]) < 2:
        errors["name"] = "Enter your full name."
    if not EMAIL_RE.match(f["email"]):
        errors["email"] = "Enter a valid email."
    if not re.fullmatch(r"\d{10}", f["phone"]):
        errors["phone"] = "Phone must be 10 digits."
    if len(f["address"]) < 5:
        errors["address"] = "Enter your delivery address."
    if not f["city"]:
        errors["city"] = "Enter your city."
    if not re.fullmatch(r"\d{6}", f["pin"]):
        errors["pin"] = "PIN code must be 6 digits."
    payment_method = str(data.get("payment_method", "ONLINE")).strip().upper()
    if payment_method not in PAYMENT_METHODS:
        errors["payment_method"] = "Choose online payment or cash on delivery."
    if errors:
        return jsonify(error="Please fix the highlighted fields.", errors=errors), 400

    items = CartItem.query.filter_by(user_id=user.id).all()
    if not items:
        return jsonify(error="Your cart is empty."), 400

    # Re-check stock right before creating the order
    for i in items:
        if i.quantity <= 0 or i.quantity > i.book.stock:
            return jsonify(error=f"'{i.book.title}' has only {i.book.stock} in stock. "
                                 f"Please update your cart."), 400

    try:
        order = Order(
            user_id=user.id,
            total_amount=round(sum(i.book.price * i.quantity for i in items), 2),
            payment_method=payment_method,
            order_status="CONFIRMED" if payment_method == "COD" else "PLACED",
            delivery_address=(f"{f['name']} | {f['email']} | {f['phone']}\n"
                              f"{f['address']}, {f['city']} - {f['pin']}"),
        )
        for i in items:
            order.items.append(OrderItem(book_id=i.book_id, quantity=i.quantity, price=i.book.price))
        db.session.add(order)
        if payment_method == "COD":
            for item in items:
                item.book.stock -= item.quantity
            CartItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(error="Could not place the order. Please try again."), 500
    if payment_method == "COD":
        return jsonify(message="Order placed. Pay cash when it is delivered.",
                       redirect=f"/orders/{order.id}")
    return jsonify(message="Order created.", redirect=f"/payment/{order.id}")


@order_bp.route("/orders")
@login_required
def my_orders():
    user = get_current_user()
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
    return render_template("my_orders.html", orders=orders, statuses=STATUSES)


@order_bp.route("/api/orders/<int:order_id>/requests", methods=["POST"])
@login_required
def create_order_request(order_id):
    user = get_current_user()
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        return jsonify(error="Order not found."), 404

    request_type = (request.get_json(silent=True) or {}).get("request_type")
    if request_type not in ORDER_REQUEST_TYPES:
        return jsonify(error="Choose cancel, return, or exchange."), 400
    if order.order_status == "CANCELLED":
        return jsonify(error="This order has already been cancelled."), 400
    if request_type == "CANCEL" and order.order_status not in ("PLACED", "CONFIRMED"):
        return jsonify(error="Orders can only be cancelled before shipment."), 400
    if request_type in ("RETURN", "EXCHANGE") and order.order_status != "DELIVERED":
        return jsonify(error="Return and exchange requests are available after delivery."), 400
    if any(item.status == "PENDING" for item in order.requests):
        return jsonify(error="An order request is already awaiting admin review."), 409
    if any(item.status == "APPROVED" for item in order.requests):
        return jsonify(error="An order request has already been approved."), 409

    db.session.add(OrderRequest(order_id=order.id, request_type=request_type))
    db.session.commit()
    return jsonify(message=f"{request_type.title()} request sent to the admin for review.")


@order_bp.route("/orders/<int:order_id>")
@login_required
def confirmation(order_id):
    user = get_current_user()
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        abort(404)
    return render_template("order_success.html", order=order, statuses=STATUSES)
