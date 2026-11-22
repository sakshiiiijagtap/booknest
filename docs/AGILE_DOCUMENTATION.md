# BookNest - Agile Documentation

> **Honesty note:** This document contains PLANNED artefacts. Sprint reviews, retrospectives, velocity, real defects and real test results have not happened yet, so none are filled in. Update the "Status" and "Result" columns as your team actually does the work.

## 1. Product Backlog
| ID | Item | Priority | Est. (pts) | Sprint |
|---|---|---|---|---|
| PB-01 | Project setup, database models, sample data | High | 5 | 1 |
| PB-02 | User registration and login | High | 5 | 1 |
| PB-03 | Book catalogue, search, filter, sort | High | 5 | 1 |
| PB-04 | Book details page | High | 3 | 1 |
| PB-05 | Shopping cart (persisted in DB) | High | 8 | 2 |
| PB-06 | Stock and quantity validation | High | 5 | 2 |
| PB-07 | Checkout form and order creation | High | 8 | 2 |
| PB-08 | Simulated payment (success / failure / retry) | High | 8 | 3 |
| PB-09 | Order confirmation and order tracking | Medium | 5 | 3 |
| PB-10 | Admin login and access control | High | 5 | 3 |
| PB-11 | Admin book management and stock update | High | 8 | 4 |
| PB-12 | Admin orders and status update, dashboard stats | Medium | 8 | 4 |
| PB-13 | Automated tests, bug fixing, README | High | 5 | 4 |

## 2. User Stories and Acceptance Criteria
**US-01 (PB-03)** As a customer, I want to search and filter books so that I can find one quickly.
- Search matches title or author, case-insensitive.
- Category filter and price sort (low-high / high-low) work together with search.
- Each card shows cover, title, author, price and stock.

**US-02 (PB-05/06)** As a customer, I want a cart so that I can buy several books at once.
- Quantity must be a whole number greater than zero and not exceed stock.
- Out-of-stock books cannot be added.
- Cart total is calculated by the server; the cart persists after logout.

**US-03 (PB-07)** As a customer, I want to check out with my delivery details.
- All fields are validated (10-digit phone, 6-digit PIN, valid email).
- An empty cart cannot be checked out.
- Stock is re-checked before the order is created.

**US-04 (PB-08)** As a customer, I want to pay for my order (simulated).
- Success: payment SUCCESS, order CONFIRMED, stock reduced exactly once, cart cleared.
- Failure: payment FAILED, order not confirmed, stock unchanged, retry possible.
- A paid order cannot be paid twice.

**US-05 (PB-09)** As a customer, I want to track my orders (PLACED -> CONFIRMED -> SHIPPED -> DELIVERED).

**US-06 (PB-10)** As an admin, I want a protected dashboard so that customers cannot reach it.
- Anonymous users and customers are redirected / refused (403 for API calls).

**US-07 (PB-11/12)** As an admin, I want to manage books, stock and order status.
- Add/edit/delete books with validation; books used in orders cannot be deleted.
- Order status can only move forward, and only for paid orders.

## 3. Sprint Plans (planned, not yet executed)
| Sprint | Goal | Backlog items | Status |
|---|---|---|---|
| 1 | Foundation and browsing | PB-01 to PB-04 | Planned |
| 2 | Cart and checkout | PB-05 to PB-07 | Planned |
| 3 | Payment, orders and admin login | PB-08 to PB-10 | Planned |
| 4 | Admin features, testing, polish | PB-11 to PB-13 | Planned |

Add your real sprint dates, actual velocity, review notes and retrospective outcomes here once they happen.

## 4. Definition of Done
- Code runs locally without errors and follows the project structure.
- Acceptance criteria of the story are met and demonstrated.
- Inputs are validated on the server.
- Relevant automated (pytest) and manual tests pass.
- No open high-severity defects for the story.
- README / documentation updated; code reviewed by a team member.

## 5. Test Case Documentation
Automated tests are in `tests/test_booknest.py` (run `pytest -v`). **Results below are blank on purpose: fill them after you run the tests yourself.**

| ID | Scenario | Steps | Expected result | Automated test | Result |
|---|---|---|---|---|---|
| TC-01 | Book search | Search "clean", then "orwell" | Matching books only | test_search_by_title_and_author | ___ |
| TC-02 | Add to cart | Add book, qty 2 | Item in cart | test_add_and_update_cart | ___ |
| TC-03 | Update quantity | Change qty to 3 | Saved as 3 | test_add_and_update_cart | ___ |
| TC-04 | Out-of-stock book | Add stock-0 book | Rejected | test_out_of_stock_book_rejected | ___ |
| TC-05 | Invalid quantity | 0, -3, "abc" | 400 error | test_invalid_quantity | ___ |
| TC-06 | Excess quantity | qty > stock | 400 error | test_quantity_above_stock_rejected | ___ |
| TC-07 | Successful payment | Pay with success | CONFIRMED, stock reduced once | test_successful_payment_reduces_stock_once | ___ |
| TC-08 | Failed payment + retry | Fail, then retry | Stock unchanged, retry works | test_failed_payment_keeps_stock_and_allows_retry | ___ |
| TC-09 | Order confirmation | Open /orders/<id> | Shows order ID | test_successful_payment_reduces_stock_once | ___ |
| TC-10 | Stock reduction / duplicate payment | Pay twice | Second attempt refused (409) | test_successful_payment_reduces_stock_once | ___ |
| TC-11 | Admin protection | Open /admin as anonymous / customer | Redirect or 403 | test_admin_pages_blocked_* | ___ |
| TC-12 | Empty cart checkout | Checkout with empty cart | Rejected | test_empty_cart_cannot_checkout | ___ |
| TC-13 | Admin manages books/orders | Add, stock, delete, status | Works; no backward status | test_admin_can_manage_books_and_orders | ___ |

## 6. Defect Log
No defects have been recorded yet. Add real defects as you find them.

| ID | Date found | Description | Severity | Found in | Status | Fixed in |
|---|---|---|---|---|---|---|
| | | | | | | |

## 7. Risk and Impediment Log
| ID | Risk / impediment | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-01 | Overselling stock when two customers pay at once | Medium | High | Re-check stock inside payment transaction | Mitigated in code |
| R-02 | Duplicate payment processing (double click) | Medium | High | Reject if order already SUCCESS | Mitigated in code |
| R-03 | Team members' limited Flask experience | Medium | Medium | Keep code simple; pair programming | Open |
| R-04 | Time pressure near the submission | Medium | Medium | Prioritised backlog; core flow first | Open |
| R-05 | Weak default secret key / demo passwords | Low (demo) | Medium | Use env SECRET_KEY, change passwords for real use | Open |
| R-06 | Payment is simulated, not a real gateway | Certain | Low | Clearly labelled in UI | Accepted |
