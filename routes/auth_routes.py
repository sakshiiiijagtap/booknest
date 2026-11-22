import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User
from routes.helpers import safe_next

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not EMAIL_RE.match(email):
            flash("Enter a valid name and email.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
        else:
            user = User(name=name, email=email, role="customer")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            flash("Welcome to BookNest!", "success")
            return redirect(url_for("books.index"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            session.clear()
            session["user_id"] = user.id
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(safe_next(request.args.get("next")) or url_for("books.index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            user = User.query.filter_by(email=email).first()
            if not user:
                flash("No account found with this email address.", "error")
            else:
                user.set_password(new_password)
                db.session.commit()
                flash("Your password has been successfully reset! Please log in with your new password.", "success")
                return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("books.index"))
