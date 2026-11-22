from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Money columns are stored as exact DECIMAL(10,2) in MySQL (a plain FLOAT would round prices).
# asdecimal=False keeps handing normal Python floats to the rest of the code, so nothing else had to change.
MONEY = db.Numeric(10, 2, asdecimal=False)

# Import models after db exists so each model file can do "from . import db".
from .user import User          # noqa: E402,F401
from .book import Book, CATEGORIES  # noqa: E402,F401
from .cart import CartItem      # noqa: E402,F401
from .order import (Order, OrderItem, OrderRequest, STATUSES, PAYMENT_METHODS,
                    ORDER_REQUEST_TYPES, ORDER_REQUEST_STATUSES)  # noqa: E402,F401
from .payment import Payment    # noqa: E402,F401
