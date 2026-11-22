import uuid
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, abort
from models import db, Book, CartItem, Order, Payment
from routes.helpers import login_required, get_current_user

payment_bp = Blueprint("payment", __name__)


def _own_order(order_id, lock=False):
    """lock=True runs SELECT ... FOR UPDATE: a second request for the same order waits until the first finishes."""
    user = get_current_user()
    query = Order.query.filter_by(id=order_id, user_id=user.id)
    if lock:
        query = query.with_for_update().populate_existing()
    return query.first(), user


@payment_bp.route("/payment/<int:order_id>")
@login_required
def payment_page(order_id):
    order, _ = _own_order(order_id)
    if not order:
        abort(404)
    if order.order_status == "CANCELLED":
        return redirect(url_for("orders.confirmation", order_id=order.id))
    if order.payment_method == "COD":
        return redirect(url_for("orders.confirmation", order_id=order.id))
    if order.payment_status == "SUCCESS":
        return redirect(url_for("orders.confirmation", order_id=order.id))
    return render_template("payment.html", order=order)


@payment_bp.route("/api/payment/<int:order_id>/simulate", methods=["POST"])
@login_required
def simulate(order_id):
    """SIMULATED payment. No real money. 'success' or 'failed' is chosen by the user."""
    order, user = _own_order(order_id, lock=True)
    if not order:
        return jsonify(error="Order not found."), 404
    if order.order_status == "CANCELLED":
        return jsonify(error="This order has been cancelled."), 400
    if order.payment_method != "ONLINE":
        return jsonify(error="This order uses cash on delivery."), 400

    result = (request.get_json(silent=True) or {}).get("result")
    if result not in ("success", "failed"):
        return jsonify(error="Invalid payment result."), 400

    # Prevent duplicate payment processing
    if order.payment_status == "SUCCESS":
        return jsonify(error="This order is already paid.", redirect=f"/orders/{order.id}"), 409

    try:
        if result == "success":
            # Check stock again; all-or-nothing inside one transaction
            books = {}
            # Lock each book row (in id order, to avoid deadlocks) so two buyers cannot take the last copy together.
            for item in sorted(order.items, key=lambda i: i.book_id):
                book = (db.session.query(Book).filter_by(id=item.book_id)
                        .with_for_update().populate_existing().first())
                if book.stock < item.quantity:
                    raise ValueError(f"'{book.title}' no longer has enough stock "
                                     f"(available: {book.stock}).")
                books[item.id] = book
            for item in order.items:
                books[item.id].stock -= item.quantity      # reduce stock exactly once
            status = "SUCCESS"
            order.payment_status = "SUCCESS"
            order.order_status = "CONFIRMED"
            CartItem.query.filter_by(user_id=user.id).delete()
        else:
            status = "FAILED"
            order.payment_status = "FAILED"                # stock untouched, order not confirmed

        db.session.add(Payment(order_id=order.id, amount=order.total_amount,
                               payment_status=status,
                               transaction_id="TXN" + uuid.uuid4().hex[:12].upper()))
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400
    except Exception:
        db.session.rollback()
        return jsonify(error="Payment processing error. Nothing was charged."), 500

    if result == "success":
        return jsonify(message="Payment successful!", redirect=f"/orders/{order.id}")
    return jsonify(message="Payment failed. You can retry.", failed=True), 200
