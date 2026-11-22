from models import db, User, Book


def seed_data():
    """Adds sample users and books the first time the app runs (only if tables are empty)."""
    if User.query.count() == 0:
        admin = User(name="BookNest Admin", email="admin@booknest.com", role="admin")
        admin.set_password("Admin@123")
        customer = User(name="Demo Customer", email="customer@booknest.com", role="customer")
        customer.set_password("Customer@123")
        db.session.add_all([admin, customer])

    if Book.query.count() == 0:
        P, CS, DSA, AI, F, SD, B = ("Programming", "Computer Science", "Data Structures and Algorithms",
                                    "Artificial Intelligence", "Fiction", "Self Development", "Business")
        # (title, author, category, price in INR, stock, description)
        rows = [
            ("Clean Code", "Robert C. Martin", P, 799, 25, "A handbook of agile software craftsmanship. Learn to write readable, maintainable code."),
            ("The Pragmatic Programmer", "Andrew Hunt, David Thomas", P, 849, 18, "Practical advice and habits that help programmers grow into better engineers."),
            ("Python Crash Course", "Eric Matthes", P, 699, 30, "A hands-on, project-based introduction to Python for beginners."),
            ("Eloquent JavaScript", "Marijn Haverbeke", P, 599, 3, "A modern introduction to JavaScript, programming and the browser."),
            ("Operating System Concepts", "Abraham Silberschatz", CS, 899, 12, "The classic text on processes, memory, file systems and scheduling."),
            ("Code", "Charles Petzold", CS, 749, 9, "The hidden language of computer hardware and software, explained from the ground up."),
            ("Introduction to Algorithms", "Thomas H. Cormen", DSA, 1299, 15, "The comprehensive reference on algorithms, widely used in university courses."),
            ("Cracking the Coding Interview", "Gayle Laakmann McDowell", DSA, 899, 2, "190 programming questions and solutions to prepare for technical interviews."),
            ("Artificial Intelligence: A Modern Approach", "Stuart Russell, Peter Norvig", AI, 1499, 8, "The leading textbook on AI, covering search, logic, learning and more."),
            ("Hands-On Machine Learning", "Aurelien Geron", AI, 1199, 0, "Build intelligent systems using Scikit-Learn, Keras and TensorFlow."),
            ("The Alchemist", "Paulo Coelho", F, 299, 40, "A shepherd boy's journey to follow his dream and find his personal legend."),
            ("1984", "George Orwell", F, 349, 22, "A dystopian novel about surveillance, truth and control."),
            ("Atomic Habits", "James Clear", SD, 499, 50, "An easy and proven way to build good habits and break bad ones."),
            ("Deep Work", "Cal Newport", SD, 449, 4, "Rules for focused success in a distracted world."),
            ("The Lean Startup", "Eric Ries", B, 549, 14, "How constant innovation creates radically successful businesses."),
            ("Zero to One", "Peter Thiel", B, 499, 0, "Notes on startups, or how to build the future."),
        ]
        for title, author, cat, price, stock, desc in rows:
            db.session.add(Book(title=title, author=author, category=cat, price=price,
                                stock=stock, description=desc, image_url=""))
    db.session.commit()
