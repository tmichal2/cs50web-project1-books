import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# def main():
#     f = open("books.csv")
#     reader = csv.reader(f)
#     reader.__next__
#     for isbn, title, author, year in reader:
#         db.execute("INSERT INTO books_tmp (isbn, title, author, year) VALUES(:isbn, :title, :author, :year)", {
#                    "isbn": isbn,
#                    "title": title,
#                    "author": author,
#                    "year": year})
#     db.commit()


def main():
    f = open("books.csv")
    reader = csv.reader(f)
    reader.__next__
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO authors (name) VALUES(:author) ON CONFLICT (name) DO NOTHING",
                   {"author": author})
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES(:isbn, :title, (SELECT author_id FROM authors WHERE name = :author), :year)", {
                   "isbn": isbn,
                   "author": author,
                   "title": title,
                   "year": year})
    db.commit()


if __name__ == "__main__":
    main()
