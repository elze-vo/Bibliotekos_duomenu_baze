from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize
import re

books_bp = Blueprint("books", __name__)

def serialize_id(doc):
    """Convert Mongo _id to string."""
    doc["_id"] = str(doc["_id"])
    return doc


# -------------------------------
# Get all books (readers + admins)
# -------------------------------
@books_bp.route("/books", methods=["GET"])
@authorize(["reader", "admin"])
def get_books():
    """
    Get all books (admin & reader)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    summary: Retrieve all books
    description: |
      Retrieve a complete list of all books in the database.  
      Accessible by both **readers** and **admins**.
    responses:
      200:
        description: A list of all books
    """
    books = [serialize_id(b) for b in db.books.find()]
    return jsonify(books)


# -------------------------------
# Search books (readers + admins)
# -------------------------------
@books_bp.route("/books/search", methods=["GET"])
@authorize(["reader", "admin"])
def search_books():
    """
    Search and filter books (admin & reader)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    summary: Search and filter books
    description: |
      Search for books by keyword, type, genre, and tags.  
      Multiple tags or genres can be entered **comma-separated** (e.g. `fantasy,romance`).  

    parameters:
      - name: keyword
        in: query
        type: string
        description: Keyword to search in title or author
        example: "Orwell"
      - name: book_type
        in: query
        type: string
        enum: [fiction, non-fiction]
        description: Filter by book type (single choice)
        example: fiction
      - name: literary_genre
        in: query
        type: string
        description: Comma-separated genres (e.g., "romanas, poezija")
        example: "romanas, poezija"
      - name: tags
        in: query
        type: string
        description: Comma-separated tags (e.g., "klasika, fantastika, istorinis")
        example: "klasika, fantastika, istorinis"
      - name: sort_by
        in: query
        type: string
        enum: [publishing_year, original_year]
        default: publishing_year
        description: Sort results by field
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: asc
        description: Sort order (ascending or descending)
    responses:
      200:
        description: Filtered list of books
    """
    # ✅ Initialize query dictionary first
    query = {}

    keyword = request.args.get("keyword", "").strip()
    book_type = request.args.get("book_type")
    tags = request.args.get("tags", "")
    literary_genre = request.args.get("literary_genre", "")
    sort_by = request.args.get("sort_by", "publishing_year")
    order = request.args.get("order", "asc")

    # Keyword search
    if keyword:
        regex = re.compile(keyword, re.IGNORECASE)
        query["$or"] = [{"title": {"$regex": regex}}, {"author": {"$regex": regex}}]

    # Filter by book_type
    if book_type:
        query["book_type"] = book_type

    # Filter by tags (comma-separated)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        query["tags"] = {"$in": tag_list}

    # Filter by literary_genre (comma-separated)
    if literary_genre:
        genre_list = [g.strip() for g in literary_genre.split(",") if g.strip()]
        query["literary_genre"] = {"$in": genre_list}

    sort_order = 1 if order == "asc" else -1

    books = [serialize_id(b) for b in db.books.find(query).sort(sort_by, sort_order)]
    return jsonify(books)

# -------------------------------
# Add a new book (admin only)
# -------------------------------
@books_bp.route("/books", methods=["POST"])
@authorize(["admin"])
def add_book():
    """
    Add a new book (admin)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    summary: Add a new book to the library
    description: |
      Allows an **admin** to add a new book to the database.  
      The `_id` field must be provided and should be a valid ISBN-13 (e.g., starts with 978 and followed by 10 digits).
    consumes:
      - application/json
    parameters:
      - in: body
        name: book
        required: true
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "9780000000030"
            title:
              type: string
              example: "The Example Book"
            author:
              type: string
              example: "John Doe"
            book_type:
              type: string
              example: "fiction"
            literary_genre:
              type: string
              example: "fantasy"
            original_year:
              type: integer
              example: 2005
            tags:
              type: array
              items:
                type: string
              example: ["magic", "dragons"]
            publishing_year:
              type: integer
              example: 2005
    responses:
      201:
        description: Book successfully added
      400:
        description: Invalid or missing ISBN (_id)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Book data required"}), 400

    book_id = data.get("_id")
    if not book_id:
        return jsonify({"error": "_id field is required"}), 400

    # Validate ISBN-13: starts with 978 and followed by 10 digits
    if not re.fullmatch(r"978\d{10}", book_id):
        return jsonify({"error": "Invalid _id. Must be a valid ISBN-13 starting with 978"}), 400

    # Check uniqueness
    existing = db.books.find_one({"_id": book_id})
    if existing:
        return jsonify({"error": f"Book with _id {book_id} already exists"}), 400

    # Insert book
    db.books.insert_one(data)
    return jsonify({"message": "Book added", "_id": book_id}), 201



# -------------------------------
# Update book (admin only)
# -------------------------------
@books_bp.route("/books/<book_id>", methods=["PUT"])
@authorize(["admin"])
def update_book(book_id):
    """
    Update book details (admin)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    summary: Update existing book details
    description: |
      Allows an **admin** to modify book details by providing the book ID.  
      Any field (e.g. title, author, year, genre, or tags) can be updated.
    consumes:
      - application/json
    parameters:
      - name: book_id
        in: path
        type: string
        required: true
        description: ID of the book to update
      - in: body
        name: book
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
              example: "Updated Title"
            author:
              type: string
              example: "Updated Author"
            publishing_year:
              type: integer
              example: 2020
            literary_genre:
              type: string
              example: "drama"
            tags:
              type: array
              items:
                type: string
              example: ["classic", "award-winning"]
    responses:
      200:
        description: Book updated successfully
      404:
        description: Book not found
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No update data provided"}), 400

    result = db.books.update_one({"_id": book_id}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Book not found"}), 404

    return jsonify({"message": "Book updated successfully"}), 200



# -------------------------------
# Delete book (admin only)
# -------------------------------
@books_bp.route("/books/<book_id>", methods=["DELETE"])
@authorize(["admin"])
def delete_book(book_id):
    """
    Delete a book (admin)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    summary: Remove a book from the library
    description: |
      Allows an **admin** to permanently delete a book by its ID. 
    parameters:
      - name: book_id
        in: path
        type: string
        required: true
        description: ID of the book to delete
    responses:
      200:
        description: Book deleted successfully
      404:
        description: Book not found
    """
    result = db.books.delete_one({"_id": book_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"message": "Book deleted successfully"}), 200
