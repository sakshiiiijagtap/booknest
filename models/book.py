from . import db, MONEY

CATEGORIES = [
    "Programming",
    "Computer Science",
    "Data Structures and Algorithms",
    "Artificial Intelligence",
    "Fiction",
    "Self Development",
    "Business",
]


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(MONEY, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), default="")  # empty -> a styled CSS cover is shown
