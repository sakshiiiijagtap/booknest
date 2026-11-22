from flask import Blueprint, render_template, request, jsonify
from models import db, Book, CartItem
from routes.helpers import login_required, get_current_user

cart_bp = Blueprint("cart", __name__)


def parse_quantity(value):
    """Returns a positive int or None."""
    try:
        qty = int(value)
    except (TypeError, ValueError):
        return None
    return qty if qty > 0 else None


def cart_count(user_id):
    return sum(i.quantity for i in CartItem.query.filter_by(user_id=user_id))


@cart_bp.route("/cart")
@login_required
def view_cart():
    user = get_current_user()
    items = CartItem.query.filter_by(user_id=user.id).all()
    total = sum(i.book.price * i.quantity for i in items)  # always calculated on the server
    return render_template("cart.html", items=items, total=total)


@cart_bp.route("/api/cart/add", methods=["POST"])
@login_required
def add():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    qty = parse_quantity(data.get("quantity", 1))
    book = db.session.get(Book, data.get("book_id")) if isinstance(data.get("book_id"), int) else None

    if qty is None:
        return jsonify(error="Quantity must be a whole number greater than zero."), 400
    if not book:
        return jsonify(error="Book not found."), 404
    if book.stock <= 0:
        return jsonify(error=f"'{book.title}' is out of stock."), 400

    item = CartItem.query.filter_by(user_id=user.id, book_id=book.id).first()
    new_qty = qty + (item.quantity if item else 0)
    if new_qty > book.stock:
        return jsonify(error=f"Only {book.stock} copies available (you already have "
                             f"{item.quantity if item else 0} in your cart)."), 400
    if item:
        item.quantity = new_qty
    else:
        db.session.add(CartItem(user_id=user.id, book_id=book.id, quantity=qty))
    db.session.commit()
    return jsonify(message="Added to cart.", cart_count=cart_count(user.id))


@cart_bp.route("/api/cart/update", methods=["POST"])
@login_required
def update():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    item = CartItem.query.filter_by(id=data.get("item_id"), user_id=user.id).first()
    qty = parse_quantity(data.get("quantity"))
    if not item:
        return jsonify(error="Cart item not found."), 404
    if qty is None:
        return jsonify(error="Quantity must be a whole number greater than zero."), 400
    if qty > item.book.stock:
        return jsonify(error=f"Only {item.book.stock} copies of '{item.book.title}' available."), 400
    item.quantity = qty
    db.session.commit()
    return jsonify(message="Cart updated.", cart_count=cart_count(user.id))


@cart_bp.route("/api/cart/remove", methods=["POST"])
@login_required
def remove():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    item = CartItem.query.filter_by(id=data.get("item_id"), user_id=user.id).first()
    if not item:
        return jsonify(error="Cart item not found."), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify(message="Removed from cart.", cart_count=cart_count(user.id))
