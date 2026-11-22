import pytest
import sqlite3
from sqlalchemy import inspect
from app import create_app
from models import db, Book, Order, OrderRequest, Payment, CartItem


def book_with(stock_min=1, stock_max=None, stock=None):
    q = Book.query
    if stock is not None:
        return q.filter_by(stock=stock).first()
    q = q.filter(Book.stock >= stock_min)
    if stock_max is not None:
        q = q.filter(Book.stock <= stock_max)
    return q.first()


def add(client, book_id, qty):
    return client.post("/api/cart/add", json={"book_id": book_id, "quantity": qty})


ADDRESS = dict(name="Test User", email="t@example.com", phone="9876543210",
               address="12 MG Road", city="Pune", pin="411001")


def make_order(client, app, qty=2):
    with app.app_context():
        b = book_with(stock_min=5)
        bid, before = b.id, b.stock
    add(client, bid, qty)
    r = client.post("/api/checkout", json=ADDRESS)
    assert r.status_code == 200
    return int(r.get_json()["redirect"].rsplit("/", 1)[1]), bid, before


def make_cod_order(client, app, qty=2):
    with app.app_context():
        b = book_with(stock_min=5)
        bid, before = b.id, b.stock
    add(client, bid, qty)
    r = client.post("/api/checkout", json=dict(ADDRESS, payment_method="COD"))
    assert r.status_code == 200 and r.get_json()["redirect"].startswith("/orders/")
    return int(r.get_json()["redirect"].rsplit("/", 1)[1]), bid, before


# 1. search
def test_search_by_title_and_author(client):
    assert b"Clean Code" in client.get("/books?q=clean").data
    assert b"Orwell" in client.get("/books?q=orwell").data
    assert b"Clean Code" not in client.get("/books?q=orwell").data


# 2. add to cart  /  3. update quantity
def test_add_and_update_cart(app, customer):
    with app.app_context():
        bid = book_with(stock_min=5).id
    assert add(customer, bid, 2).status_code == 200
    with app.app_context():
        item = CartItem.query.first()
        iid = item.id
    assert customer.post("/api/cart/update", json={"item_id": iid, "quantity": 3}).status_code == 200
    with app.app_context():
        assert db.session.get(CartItem, iid).quantity == 3


# 4. out of stock
def test_out_of_stock_book_rejected(app, customer):
    with app.app_context():
        bid = book_with(stock=0).id
    r = add(customer, bid, 1)
    assert r.status_code == 400 and "out of stock" in r.get_json()["error"]


# 5. invalid quantity
@pytest.mark.parametrize("qty", [0, -3, "abc", None])
def test_invalid_quantity(app, customer, qty):
    with app.app_context():
        bid = book_with(stock_min=5).id
    assert add(customer, bid, qty).status_code == 400


# 6. excess quantity
def test_quantity_above_stock_rejected(app, customer):
    with app.app_context():
        b = book_with(stock_min=1, stock_max=5)
        bid, stock = b.id, b.stock
    assert add(customer, bid, stock + 1).status_code == 400


def test_empty_cart_cannot_checkout(customer):
    assert customer.post("/api/checkout", json=ADDRESS).status_code == 400


def test_cod_checkout_reserves_stock_and_cannot_use_online_payment(app, customer):
    oid, bid, before = make_cod_order(customer, app, qty=2)
    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.payment_method == "COD"
        assert order.order_status == "CONFIRMED"
        assert order.payment_status == "PENDING"
        assert db.session.get(Book, bid).stock == before - 2
        assert CartItem.query.count() == 0
    order_page = customer.get("/orders")
    assert b"Request cancellation" in order_page.data
    assert b"Request return" in order_page.data
    assert b"Request exchange" in order_page.data
    assert b'data-request="CANCEL"\n      disabled' not in order_page.data
    assert b'data-request="RETURN"\n      disabled' in order_page.data
    assert customer.get(f"/payment/{oid}").status_code == 302
    assert customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"}).status_code == 400


def test_invalid_payment_method_rejected(app, customer):
    with app.app_context():
        add(customer, book_with(stock_min=5).id, 1)
    response = customer.post("/api/checkout", json=dict(ADDRESS, payment_method="WIRE"))
    assert response.status_code == 400
    assert "payment_method" in response.get_json()["errors"]


def test_cancel_request_requires_admin_and_restores_reserved_stock(app, customer):
    oid, bid, before = make_cod_order(customer, app, qty=2)
    response = customer.post(f"/api/orders/{oid}/requests", json={"request_type": "CANCEL"})
    assert response.status_code == 200
    with app.app_context():
        order_request = OrderRequest.query.filter_by(order_id=oid).one()
        request_id = order_request.id
        assert order_request.status == "PENDING"
        assert db.session.get(Book, bid).stock == before - 2

    admin = app.test_client()
    admin.post("/admin/login", data={"email": "admin@booknest.com", "password": "Admin@123"})
    page = admin.get("/admin/orders")
    assert b"Cash on delivery" in page.data and b"Cancel" in page.data
    resolved = admin.post(f"/admin/order-requests/{request_id}/resolve", json={"decision": "approve"})
    assert resolved.status_code == 200
    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.order_status == "CANCELLED"
        assert order.requests[0].status == "APPROVED"
        assert db.session.get(Book, bid).stock == before
    assert b"This order has been cancelled" in customer.get(f"/orders/{oid}").data
    assert customer.get(f"/payment/{oid}").status_code == 302


def test_return_and_exchange_only_after_delivery(app, customer):
    oid, _, _ = make_order(customer, app)
    customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"})
    assert customer.post(f"/api/orders/{oid}/requests", json={"request_type": "RETURN"}).status_code == 400
    admin = app.test_client()
    admin.post("/admin/login", data={"email": "admin@booknest.com", "password": "Admin@123"})
    assert admin.post(f"/admin/orders/{oid}/status", json={"status": "SHIPPED"}).status_code == 200
    shipped_orders_page = customer.get("/orders").data
    assert b"Cancellation unavailable" in shipped_orders_page
    assert b'data-request="RETURN"\n      disabled' in shipped_orders_page
    assert admin.post(f"/admin/orders/{oid}/status", json={"status": "DELIVERED"}).status_code == 200
    delivered_orders_page = customer.get("/orders").data
    assert b'data-request="RETURN"\n      disabled' not in delivered_orders_page
    assert b'data-request="EXCHANGE"\n      disabled' not in delivered_orders_page
    assert customer.post(f"/api/orders/{oid}/requests", json={"request_type": "EXCHANGE"}).status_code == 200
    with app.app_context():
        order_request = OrderRequest.query.filter_by(order_id=oid).one()
        assert order_request.request_type == "EXCHANGE" and order_request.status == "PENDING"
    assert b"Exchange request" in customer.get("/orders").data


def test_existing_database_gets_payment_method_column(tmp_path):
    database_path = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
        "order_date DATETIME, total_amount FLOAT NOT NULL, order_status VARCHAR(20) NOT NULL, "
        "payment_status VARCHAR(20) NOT NULL, delivery_address TEXT NOT NULL)"
    )
    connection.close()

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "migration-test",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(database_path).replace("\\", "/"),
    })
    with app.app_context():
        columns = {column["name"] for column in inspect(db.engine).get_columns("orders")}
        assert "payment_method" in columns


# 7. successful payment  /  9. confirmation  /  10. stock reduction
def test_successful_payment_reduces_stock_once(app, customer):
    oid, bid, before = make_order(customer, app, qty=2)
    r = customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"})
    assert r.status_code == 200
    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.payment_status == "SUCCESS" and order.order_status == "CONFIRMED"
        assert db.session.get(Book, bid).stock == before - 2
        assert CartItem.query.count() == 0
    # duplicate payment must be refused and stock must not change again
    assert customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"}).status_code == 409
    with app.app_context():
        assert db.session.get(Book, bid).stock == before - 2
        assert Payment.query.filter_by(order_id=oid).count() == 1
    assert b"BN%05d" % oid in customer.get(f"/orders/{oid}").data


# 8. failed payment, then retry
def test_failed_payment_keeps_stock_and_allows_retry(app, customer):
    oid, bid, before = make_order(customer, app, qty=2)
    assert customer.post(f"/api/payment/{oid}/simulate", json={"result": "failed"}).status_code == 200
    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.payment_status == "FAILED" and order.order_status == "PLACED"
        assert db.session.get(Book, bid).stock == before
    assert customer.get(f"/payment/{oid}").status_code == 200           # retry page opens
    assert customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"}).status_code == 200
    with app.app_context():
        assert db.session.get(Book, bid).stock == before - 2


def test_stock_rechecked_at_payment(app, customer):
    oid, bid, _ = make_order(customer, app, qty=2)
    with app.app_context():
        db.session.get(Book, bid).stock = 1          # someone else bought it meanwhile
        db.session.commit()
    r = customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"})
    assert r.status_code == 400
    with app.app_context():
        assert db.session.get(Order, oid).payment_status == "PENDING"
        assert db.session.get(Book, bid).stock == 1


def test_checkout_validation(app, customer):
    with app.app_context():
        add(customer, book_with(stock_min=5).id, 1)
    bad = dict(ADDRESS, phone="123", pin="12")
    r = customer.post("/api/checkout", json=bad)
    assert r.status_code == 400 and {"phone", "pin"} <= set(r.get_json()["errors"])


def test_cannot_view_other_users_order(app, customer, client):
    oid, _, _ = make_order(customer, app)
    other = app.test_client()
    other.post("/register", data={"name": "Other", "email": "o@example.com", "password": "secret1"})
    assert other.get(f"/orders/{oid}").status_code == 404


# 11. admin access protection
@pytest.mark.parametrize("url", ["/admin/", "/admin/books", "/admin/orders", "/admin/books/add"])
def test_admin_pages_blocked_for_anonymous(client, url):
    r = client.get(url)
    assert r.status_code == 302 and "/admin/login" in r.headers["Location"]


def test_admin_pages_blocked_for_customer(customer):
    assert customer.get("/admin/").status_code == 302
    assert customer.post("/admin/books/1/stock", json={"stock": 5}).status_code == 403


def test_admin_can_manage_books_and_orders(app, customer):
    oid, _, _ = make_order(customer, app)
    customer.post(f"/api/payment/{oid}/simulate", json={"result": "success"})
    admin = app.test_client()
    assert admin.post("/admin/login", data={"email": "admin@booknest.com", "password": "Admin@123"}).status_code == 302
    assert admin.get("/admin/").status_code == 200
    r = admin.post("/admin/books/add", data={"title": "New Book", "author": "Me", "category": "Fiction",
                                             "price": "199", "stock": "7", "description": "x", "image_url": ""})
    assert r.status_code == 302
    with app.app_context():
        nb = Book.query.filter_by(title="New Book").first()
        assert nb and nb.stock == 7
        nid = nb.id
    assert admin.post(f"/admin/books/{nid}/stock", json={"stock": 20}).status_code == 200
    assert admin.post(f"/admin/books/{nid}/delete").status_code == 200
    assert admin.post(f"/admin/orders/{oid}/status", json={"status": "SHIPPED"}).status_code == 200
    assert admin.post(f"/admin/orders/{oid}/status", json={"status": "CONFIRMED"}).status_code == 400  # no going back
