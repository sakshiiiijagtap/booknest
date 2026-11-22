from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from models import db, User


def get_current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def _wants_json():
    return request.path.startswith("/api") or request.is_json


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            if _wants_json():
                return jsonify(error="Please log in first."), 401
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Server-side access control: checks the role stored in the database, not in the browser."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != "admin":
            if _wants_json():
                return jsonify(error="Admin access required."), 403
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return wrapper


def safe_next(target):
    """Only allow redirects to our own pages."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None
