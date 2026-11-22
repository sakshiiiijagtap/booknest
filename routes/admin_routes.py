from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from sqlalchemy import func
from models import (db, User, Book, CartItem, Order, OrderItem, OrderRequest, STATUSES,
                    CATEGORIES)
from routes.helpers import admin_required, get_current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.role == "admin" and user.check_password(request.form.get("password", "")):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/")
@admin_required
def dashboard():
    paid = Order.query.filter(Order.payment_status == "SUCCESS", Order.order_status != "CANCELLED")
    stats = {
        "books": Book.query.count(),
        "orders": Order.query.count(),
        "customers": User.query.filter_by(role="customer").count(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
                     .filter(Order.payment_status == "SUCCESS", Order.order_status != "CANCELLED").scalar(),
        "paid_orders": paid.count(),
        "low_stock": Book.query.filter(Book.stock > 0, Book.stock <= 5).count(),
        "out_of_stock": Book.query.filter(Book.stock == 0).count(),
    }
    recent = Order.query.order_by(Order.id.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


# ---------- Books ----------
@admin_bp.route("/books")
@admin_required
def books():
    return render_template("admin/books.html", books=Book.query.order_by(Book.id).all())


def read_book_form(form):
    """Returns (cleaned_values, error_message)."""
    title = form.get("title", "").strip()
    author = form.get("author", "").strip()
    category = form.get("category", "")
    try:
        price = float(form.get("price", ""))
        stock = int(form.get("stock", ""))
    except ValueError:
        return None, "Price must be a number and stock a whole number."
    if not title or not author:
        return None, "Title and author are required."
    if category not in CATEGORIES:
        return None, "Choose a valid category."
    if price <= 0:
        return None, "Price must be greater than zero."
    if stock < 0:
        return None, "Stock cannot be negative."
    return dict(title=title, author=author, category=category, price=round(price, 2), stock=stock,
                description=form.get("description", "").strip(),
                image_url=form.get("image_url", "").strip()), None


@admin_bp.route("/books/add", methods=["GET", "POST"])
@admin_required
def add_book():
    if request.method == "POST":
        values, error = read_book_form(request.form)
        if error:
            flash(error, "error")
        else:
            db.session.add(Book(**values))
            db.session.commit()
            flash("Book added.", "success")
            return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html", book=None, categories=CATEGORIES)


@admin_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    book = db.session.get(Book, book_id) or abort(404)
    if request.method == "POST":
        values, error = read_book_form(request.form)
        if error:
            flash(error, "error")
        else:
            for k, v in values.items():
                setattr(book, k, v)
            db.session.commit()
            flash("Book updated.", "success")
            return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html", book=book, categories=CATEGORIES)


@admin_bp.route("/books/<int:book_id>/delete", methods=["POST"])
@admin_required
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify(error="Book not found."), 404
    if OrderItem.query.filter_by(book_id=book.id).first():
        return jsonify(error="This book is part of existing orders, so it cannot be deleted. "
                             "Set its stock to 0 instead."), 400
    CartItem.query.filter_by(book_id=book.id).delete()
    db.session.delete(book)
    db.session.commit()
    return jsonify(message="Book deleted.")


@admin_bp.route("/books/<int:book_id>/stock", methods=["POST"])
@admin_required
def update_stock(book_id):
    book = db.session.get(Book, book_id)
    data = request.get_json(silent=True) or {}
    try:
        stock = int(data.get("stock"))
    except (TypeError, ValueError):
        return jsonify(error="Stock must be a whole number."), 400
    if not book:
        return jsonify(error="Book not found."), 404
    if stock < 0:
        return jsonify(error="Stock cannot be negative."), 400
    book.stock = stock
    db.session.commit()
    return jsonify(message="Stock updated.", stock=book.stock)


# ---------- Orders ----------
@admin_bp.route("/orders")
@admin_required
def orders():
    return render_template("admin/orders.html", orders=Order.query.order_by(Order.id.desc()).all(),
                           statuses=STATUSES)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    new_status = (request.get_json(silent=True) or {}).get("status")
    if not order:
        return jsonify(error="Order not found."), 404
    if new_status not in STATUSES:
        return jsonify(error="Invalid status."), 400
    if order.order_status == "CANCELLED":
        return jsonify(error="Cancelled orders cannot be updated."), 400
    if order.payment_status != "SUCCESS" and order.payment_method != "COD":
        return jsonify(error="Only paid or cash-on-delivery orders can be updated."), 400
    if STATUSES.index(new_status) <= order.status_index:
        return jsonify(error="Status can only move forward."), 400
    order.order_status = new_status
    db.session.commit()
    return jsonify(message=f"Order marked {new_status}.", status=new_status)


@admin_bp.route("/order-requests/<int:request_id>/resolve", methods=["POST"])
@admin_required
def resolve_order_request(request_id):
    order_request = db.session.get(OrderRequest, request_id)
    if not order_request:
        return jsonify(error="Order request not found."), 404
    if order_request.status != "PENDING":
        return jsonify(error="This request has already been reviewed."), 409

    decision = (request.get_json(silent=True) or {}).get("decision")
    if decision not in ("approve", "reject"):
        return jsonify(error="Choose approve or reject."), 400

    order = order_request.order
    if decision == "approve" and order_request.request_type == "CANCEL":
        if order.order_status not in ("PLACED", "CONFIRMED"):
            return jsonify(error="This order has already shipped and can no longer be cancelled."), 400
        if order.payment_method == "COD" or order.payment_status == "SUCCESS":
            for item in order.items:
                item.book.stock += item.quantity
        order.order_status = "CANCELLED"

    order_request.status = "APPROVED" if decision == "approve" else "REJECTED"
    order_request.resolved_at = datetime.now()
    db.session.commit()
    return jsonify(message=f"Request {order_request.status.lower()}.",
                   status=order_request.status)


# ---------- Users ----------
@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=all_users)

