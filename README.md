# BookNest - Online Bookstore (Flask + MySQL)

Stack: HTML5, CSS3, vanilla JavaScript (Fetch API), Python Flask, **MySQL 8** with Flask-SQLAlchemy (PyMySQL driver), Jinja2, Werkzeug password hashing. No JS frameworks.

> This project was migrated from SQLite to MySQL. Tables, the sample data and the tests all run on MySQL.

## Run locally
1. Install **MySQL 8** and make sure it is running on port 3306.
2. Tell the app your MySQL login (the database `booknest` is created for you):
```bash
# Windows PowerShell
$env:MYSQL_PASSWORD="your_mysql_password"
# macOS / Linux
export MYSQL_PASSWORD="your_mysql_password"
```
Optional variables: `MYSQL_USER` (default `root`), `MYSQL_HOST` (`localhost`), `MYSQL_PORT` (`3306`), `MYSQL_DB` (`booknest`).
Or set one full URL: `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/booknest?charset=utf8mb4`.
3. Install and run:
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. On first run the app creates the database, all tables and the sample data (16 books, 2 users). To reset: in MySQL run `DROP DATABASE booknest;` and start the app again.

If MySQL 8 reports "Access denied" for root, use a password you set yourself, or create a user:
`CREATE USER 'bn'@'localhost' IDENTIFIED BY 'secret'; GRANT ALL ON booknest.* TO 'bn'@'localhost';` then set `MYSQL_USER=bn`.

## Open the database
MySQL Workbench -> connect to localhost:3306 -> schema `booknest`. Or: `mysql -u root -p` then `USE booknest; SHOW TABLES; SELECT id, title, stock FROM books;`

## Run the tests
```bash
python -m pytest            # fast, uses an in-memory SQLite database
# same tests against real MySQL (creates/empties the booknest_test database):
# PowerShell:  $env:TEST_DATABASE_URL="mysql+pymysql://root:PASSWORD@localhost:3306/booknest_test?charset=utf8mb4"
# Mac/Linux:   export TEST_DATABASE_URL="mysql+pymysql://root:PASSWORD@localhost:3306/booknest_test?charset=utf8mb4"
python -m pytest
```
If your password contains symbols such as @ or #, URL-encode them in `TEST_DATABASE_URL` (@ becomes %40, # becomes %23).

## What changed in the MySQL migration
- `config.py`: MySQL connection built from environment variables.
- `app.py`: creates the `booknest` database if missing.
- Money columns (price, total, amount) changed from FLOAT to exact `DECIMAL(10,2)`; Python code still receives normal numbers.
- `routes/payment_routes.py`: added row locks (`SELECT ... FOR UPDATE`) so two simultaneous payments for one order, or two buyers of the last copy, cannot double-pay or oversell. SQLite cannot do this.
- `requirements.txt`: added PyMySQL and cryptography.

## Demo accounts
| Role | Email | Password |
|---|---|---|
| Customer | customer@booknest.com | Customer@123 |
| Admin | admin@booknest.com | Admin@123 |

Admin panel: http://127.0.0.1:5000/admin/login

## Run tests
```bash
pytest -v
```

## Demo script for the viva
1. Search "orwell" on Books -> open **1984** -> choose quantity -> Add to Cart.
2. Open **Hands-On Machine Learning** (stock 0): the button is disabled, and the API also rejects it.
3. Try quantity above stock on **Cracking the Coding Interview** (stock 2): error toast.
4. Cart -> change quantity -> Checkout -> fill form -> choose simulated online payment or cash on delivery.
5. For online payment, click **Simulate Failed Payment** -> order stays unpaid, stock unchanged -> retry with **Simulate Successful Payment**.
6. Order confirmation -> My Orders (tracker PLACED -> CONFIRMED -> SHIPPED -> DELIVERED).
7. Log in as admin: dashboard, add/edit/delete book, update stock, move the order to SHIPPED.

Customers can request cancellation before shipment, or request a return/exchange after delivery. Admins approve or reject these requests from the Orders page. Payment is prototype-only: online payment is simulated, COD is recorded for admin visibility, and return/exchange approval does not process a real refund or shipment.

## How it works (short)
- `models/` - 6 tables: User, Book, CartItem, Order, OrderItem, Payment (foreign keys + relationships).
- `routes/` - one Flask Blueprint per feature. `helpers.py` holds `login_required` / `admin_required`.
- The cart lives in the `cart_items` table, so it survives logout.
- Prices and totals are always calculated on the server. The browser only sends book ids and quantities.
- Checkout creates an Order with payment `PENDING`. **Stock changes only inside the successful-payment transaction**, which re-checks stock first and refuses a second payment for the same order.
- Admin access is checked on the server from the role stored in the database.

## Design choices worth knowing
- A book that already appears in an order cannot be deleted (it would break order history). Set stock to 0 instead.
- Order status can only move forward and only after payment succeeds.
- Covers: if a book has an image URL (admin form) that is used. Otherwise the browser looks the cover up on Open Library (needs internet; results are cached in localStorage) and falls back to a generated CSS cover if none is found.
- Set `SECRET_KEY` as an environment variable for anything beyond a demo.
