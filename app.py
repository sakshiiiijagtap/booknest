from flask import Flask, session, render_template
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from config import Config
from models import db, User, Book, CartItem
from seed import seed_data


def ensure_database_exists(uri):
    """MySQL will not create the database for us, so create it (empty) if it is missing."""
    url = make_url(uri)
    if not url.drivername.startswith("mysql") or not url.database:
        return  # e.g. an in-memory test database: nothing to do
    # Same server and login, but with NO database selected (url.set(database=None) would keep the old one).
    server_only = URL.create(url.drivername, username=url.username, password=url.password,
                             host=url.host, port=url.port, query=url.query)
    engine = create_engine(server_only)
    try:
        with engine.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{url.database}` "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    finally:
        engine.dispose()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    ensure_database_exists(app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)

    from routes.auth_routes import auth_bp
    from routes.book_routes import book_bp
    from routes.cart_routes import cart_bp
    from routes.order_routes import order_bp
    from routes.payment_routes import payment_bp
    from routes.admin_routes import admin_bp
    for bp in (auth_bp, book_bp, cart_bp, order_bp, payment_bp, admin_bp):
        app.register_blueprint(bp)

    @app.template_filter("inr")
    def inr(value):
        return f"₹{value:,.2f}"

    @app.context_processor
    def inject_globals():
        """Makes current_user and cart_count available in every template."""
        user = db.session.get(User, session["user_id"]) if "user_id" in session else None
        count = 0
        if user:
            count = sum(i.quantity for i in CartItem.query.filter_by(user_id=user.id))
        return {"current_user": user, "cart_count": count}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found"), 404

    with app.app_context():
        db.create_all()
        order_columns = {column["name"] for column in inspect(db.engine).get_columns("orders")}
        if "payment_method" not in order_columns:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE orders ADD COLUMN payment_method "
                    "VARCHAR(20) NOT NULL DEFAULT 'ONLINE'"
                ))
        seed_data()
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
