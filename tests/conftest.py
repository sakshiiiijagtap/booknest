import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app
from models import db


@pytest.fixture()
def app():
    # Fast default: in-memory SQLite. To run the same tests against MySQL:
    #   set TEST_DATABASE_URL=mysql+pymysql://root:PASSWORD@localhost:3306/booknest_test?charset=utf8mb4
    uri = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": uri, "SECRET_KEY": "test"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()  # leaves the test database empty for the next test


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password})


@pytest.fixture()
def customer(client):
    login(client, "customer@booknest.com", "Customer@123")
    return client
