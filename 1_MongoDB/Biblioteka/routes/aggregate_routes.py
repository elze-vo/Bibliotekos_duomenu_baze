from flask import Blueprint, jsonify
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize

aggregate_bp = Blueprint("aggregations", __name__)

# -------------------------------
# 1️⃣ Aggregate: Count how many copies each branch has
# -------------------------------
@aggregate_bp.route("/aggregations/books_per_branch", methods=["GET"])
@authorize(["admin"])
def books_per_branch():
    """
    Aggregate: Count how many copies each branch has (admin)
    ---
    tags:
      - Aggregations
    security:
      - Bearer: []
    summary: Count the number of book copies per branch
    description: Returns how many book copies each library branch has, ordered from most to least.
    responses:
      200:
        description: Aggregated results of book copies per branch
    """
    pipeline = [
        {"$group": {"_id": "$branch_id", "total_copies": {"$sum": 1}}},
        {
            "$lookup": {
                "from": "branches",
                "localField": "_id",
                "foreignField": "_id",
                "as": "branch_info"
            }
        },
        {"$unwind": "$branch_info"},
        {
            "$project": {
                "_id": 0,
                "branch_id": "$_id",
                "branch_name": "$branch_info.name",
                "total_copies": 1
            }
        },
        {"$sort": {"total_copies": -1}}  # 🔽 sort by count descending
    ]

    result = list(db.copies.aggregate(pipeline))
    return jsonify(result), 200


# -------------------------------
# 2️⃣ Aggregate: Top 5 books with most reservations
# -------------------------------
@aggregate_bp.route("/aggregations/top_reserved_books", methods=["GET"])
@authorize(["admin"])
def top_reserved_books():
    """
    Aggregate: Top 5 books with most reservations (admin)
    ---
    tags:
      - Aggregations
    security:
      - Bearer: []
    summary: Show the top 5 books with the most reservations
    description: |
      Joins reservations → copies → books to find which books have the highest number of reservations.  
      Returns the **title**, **author**, and total reservation count.
    responses:
      200:
        description: List of top 5 reserved books
    """
    pipeline = [
        # Group by copy_id to count reservations per copy
        {"$group": {"_id": "$copy_id", "reservation_count": {"$sum": 1}}},

        # Join to copies to get the corresponding book_id
        {
            "$lookup": {
                "from": "copies",
                "localField": "_id",
                "foreignField": "_id",
                "as": "copy_info"
            }
        },
        {"$unwind": "$copy_info"},

        # Join to books to get title and author
        {
            "$lookup": {
                "from": "books",
                "localField": "copy_info.book_id",
                "foreignField": "_id",
                "as": "book_info"
            }
        },
        {"$unwind": "$book_info"},

        # Group again by book to count total reservations across all copies
        {
            "$group": {
                "_id": "$book_info._id",
                "title": {"$first": "$book_info.title"},
                "author": {"$first": "$book_info.author"},
                "total_reservations": {"$sum": "$reservation_count"}
            }
        },

        # Sort and limit to top 5
        {"$sort": {"total_reservations": -1}},
        {"$limit": 5},

        # Project clean output
        {
            "$project": {
                "_id": 0,
                "book_id": "$_id",
                "title": 1,
                "author": 1,
                "total_reservations": 1
            }
        }
    ]

    result = list(db.reservations.aggregate(pipeline))
    return jsonify(result), 200


# -------------------------------
# 3️⃣ Aggregate: Book availability summary
# -------------------------------
@aggregate_bp.route("/aggregations/book_availability_summary", methods=["GET"])
@authorize(["admin"])
def book_availability_summary():
    """
    Aggregate: Availability summary per book (admin)
    ---
    tags:
      - Aggregations
    security:
      - Bearer: []
    summary: Show how many copies of each book are available, reserved, or taken
    description: |
      Aggregates data from `copies` and `books` collections  
      to show the availability status for each book.
    responses:
      200:
        description: List of books with availability breakdown
    """
    pipeline = [
        # Group copies by book_id and count each status
        {
            "$group": {
                "_id": {"book_id": "$book_id", "status": "$status"},
                "count": {"$sum": 1}
            }
        },
        # Pivot statuses into a single document per book
        {
            "$group": {
                "_id": "$_id.book_id",
                "available": {
                    "$sum": {"$cond": [{"$eq": ["$_id.status", "available"]}, "$count", 0]}
                },
                "reserved": {
                    "$sum": {"$cond": [{"$eq": ["$_id.status", "reserved"]}, "$count", 0]}
                },
                "taken": {
                    "$sum": {"$cond": [{"$eq": ["$_id.status", "taken"]}, "$count", 0]}
                },
                "total_copies": {"$sum": "$count"}
            }
        },
        # Join to books collection to get title and author
        {
            "$lookup": {
                "from": "books",
                "localField": "_id",
                "foreignField": "_id",
                "as": "book_info"
            }
        },
        {"$unwind": "$book_info"},
        # Format output
        {
            "$project": {
                "_id": 0,
                "book_id": "$_id",
                "title": "$book_info.title",
                "author": "$book_info.author",
                "available": 1,
                "reserved": 1,
                "taken": 1,
                "total_copies": 1
            }
        },
        {"$sort": {"total_copies": -1}}
    ]

    result = list(db.copies.aggregate(pipeline))
    return jsonify(result), 200
