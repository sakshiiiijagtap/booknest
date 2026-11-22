from flask import Blueprint, render_template, request, abort
from sqlalchemy import func, or_
from models import db, Book, OrderItem, CATEGORIES

book_bp = Blueprint("books", __name__)


@book_bp.route("/")
def index():
    featured = Book.query.order_by(Book.id.desc()).limit(4).all()
    # Popular = most units sold (books never sold fall back to id order)
    popular = (db.session.query(Book)
               .outerjoin(OrderItem, OrderItem.book_id == Book.id)
               .group_by(Book.id)
               .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc(), Book.id)
               .limit(4).all())
    return render_template("index.html", featured=featured, popular=popular, categories=CATEGORIES)


@book_bp.route("/books")
def catalogue():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "")

    query = Book.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Book.title.ilike(like), Book.author.ilike(like)))
    if category in CATEGORIES:
        query = query.filter(Book.category == category)
    if sort == "price_asc":
        query = query.order_by(Book.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Book.price.desc())
    else:
        query = query.order_by(Book.title.asc())
    return render_template("books.html", books=query.all(), categories=CATEGORIES,
                           q=q, category=category, sort=sort)


@book_bp.route("/books/<int:book_id>")
def details(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    return render_template("book_details.html", book=book)
