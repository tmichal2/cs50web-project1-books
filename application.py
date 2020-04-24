import os

import requests
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_session import Session
from passlib.hash import sha256_crypt
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        search = request.form.get("book_search")

        results = db.execute(
            "SELECT books.title, books.isbn, books.year, authors.name \
            FROM books JOIN authors ON books.author=authors.author_id \
            WHERE to_tsvector(books.isbn || ' ' || books.title || ' ' || authors.name || ' ' || books.year) @@ plainto_tsquery(:search) \
            ORDER BY authors.name, books.title DESC",
            {"search": search}).fetchall()
        b = True
        if len(results) == 0:
            b = False
        return render_template("results.html", results=results, b=b)

    return render_template("search.html")


@app.route("/books/<isbn>")
def book_page(isbn):
    book = db.execute(
        "SELECT * FROM \
        books JOIN authors ON books.author=authors.author_id \
        WHERE books.isbn=:isbn", {"isbn": isbn}).fetchall()

    reviews = db.execute("SELECT review, username, rating FROM reviews JOIN users ON reviews.user_id=users.id WHERE book_id=(SELECT book_id FROM books WHERE isbn=:isbn)", {
        "isbn": isbn}).fetchall()
    print(reviews)
    reviews_exist = True
    if len(reviews) == 0:
        reviews_exist = False

    username = db.execute("SELECT username FROM users WHERE id=:user_id", {
                          "user_id": session["user_id"]}).fetchone()

    title = ""
    year = ""
    author = ""
    isbns = []
    isbns.append(isbn)

    for row in book:
        title = row[2]
        year = row[4]
        author = row[6]

    goodreads = requests.get(
        "https://www.goodreads.com/book/review_counts.json", params={"format": 'json', "isbns": isbns})
    data = goodreads.json()
    average_rating = data['books'][0]['average_rating']
    number_ratings = data['books'][0]['work_reviews_count']

    return render_template("book.html", isbn=isbn,
                           title=title,
                           year=year,
                           author=author,
                           reviews_exist=reviews_exist,
                           reviews=reviews,
                           username=username[0],
                           average_rating=average_rating,
                           number_ratings=number_ratings)


@app.route("/review/<isbn>", methods=["POST"])
@login_required
def review(isbn):
    review = request.form.get("review")
    rating = request.form.get("rating")
    # Check if user has left a review already
    if len(db.execute("SELECT * FROM reviews WHERE user_id=:user_id AND book_id=(SELECT book_id FROM books WHERE isbn=:isbn)",
                      {"user_id": session["user_id"], "isbn": isbn}).fetchall()) > 0:
        flash("You have already reviewed this book.")
        return redirect(url_for('book_page', isbn=isbn))

    # Insert review
    db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES(:user_id, (SELECT book_id FROM books WHERE isbn=:isbn), :review, :rating)",
               {"user_id": session["user_id"], "isbn": isbn, "review": review, "rating": rating})
    db.commit()
    print(review)
    print(isbn)
    return redirect(url_for('book_page', isbn=isbn))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")

        if not username:
            return render_template("login.html", error="Must Input Username")

        if not request.form.get("password"):
            return render_template("login.html", error="Must Input Password")

        user_id = db.execute(
            "SELECT * FROM users WHERE username = :username", {"username": username})

        for i in user_id:
            user_id = i[0]
            user_hash = i[2]

        if sha256_crypt.verify(request.form.get("password"), user_hash):
            session["user_id"] = user_id
            return redirect("/")

    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = sha256_crypt.hash(request.form.get("password"))

        if not email:
            return render_template("register.html", error="Invalid Email")

        if not username:
            return render_template("register.html", error="Invalid Username")

        # IF USERNAME TAKEN
        if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
            return render_template("register.html", error="Username Taken")

        if not password:
            return render_template("register.html", error="Invalid Password")

        if request.form.get("confirm_password") != request.form.get("password"):
            return render_template("register.html", error="Passwords do not match")

        db.execute("INSERT INTO users (username, password, email) VALUES(:username, :password, :email)",
                   {"username": username, "password": password, "email": email})
        db.commit()

        return redirect("/login")

    else:
        return render_template("register.html")


# Log user out
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
