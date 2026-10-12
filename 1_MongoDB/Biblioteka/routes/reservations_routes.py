from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize
from datetime import datetime

reservations_bp = Blueprint("reservations", __name__)


def serialize_id(doc):
    """Convert Mongo ObjectId to string."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def get_next_id(collection):
    """Return the next incremental _id for a Mongo collection."""
    last = db[collection].find_one(sort=[("_id", -1)])
    return (last["_id"] + 1) if last and isinstance(last["_id"], int) else 1


# -------------------------------
# GET: View reservations
# -------------------------------
@reservations_bp.route("/reservations", methods=["GET"])
@authorize(["admin", "reader"])
def get_reservations():
    """
    Get reservations (admin & reader)
    ---
    tags:
      - Reservations
    security:
      - Bearer: []
    summary: Get reservations
    description: |
      - **Reader**: Always sees only their own reservations.  
      - **Admin**: 
        - No input → sees all reservations for their **own branch**.  
        - `user_id` input → sees reservations for that user **in their branch**, **only for copies that are taken**.
    parameters:
      - name: user_id
        in: query
        type: integer
        required: false
        description: (Admin only) Filter reservations by user ID (taken books only)
        example: 42
    responses:
      200:
        description: Returns reservations with joined book info
    """
    user = getattr(request, "user", None)
    role = user.get("role")
    query = {}

    # --------------------------
    # Reader functionality
    # --------------------------
    if role == "reader":
        try:
            query["user_id"] = int(user.get("user_id"))
        except (ValueError, TypeError):
            query["user_id"] = user.get("user_id")

    # --------------------------
    # Admin functionality
    # --------------------------
    elif role == "admin":
        admin_branch_id = int(user.get("branch_id"))
        query["branch_id"] = admin_branch_id

        user_id = request.args.get("user_id", type=int)
        if user_id:
            # Filter reservations by user_id but only for copies that are currently taken
            # We'll do this after we fetch reservations, to check copy status
            query["user_id"] = user_id

    reservations = list(db.reservations.find(query))
    results = []

    for r in reservations:
        serialize_id(r)
        book_info = {}

        # --- Join reservation → copy ---
        copy = None
        try:
            copy = db.copies.find_one({"_id": int(r["copy_id"])})
        except (ValueError, TypeError):
            copy = db.copies.find_one({"_id": str(r["copy_id"])})

        # If admin searched by user_id, we only keep "taken" copies
        if role == "admin" and request.args.get("user_id") and copy and copy.get("status") != "taken":
            continue  # skip non-taken copies for admin filtering by user

        if copy:
            # --- Join copy → book ---
            book_id = copy.get("book_id")
            if book_id is not None:
                book = db.books.find_one({"_id": str(book_id)})
                if not book:
                    try:
                        book = db.books.find_one({"_id": int(book_id)})
                    except (ValueError, TypeError):
                        pass
                if book:
                    book_info = {
                        "title": book.get("title"),
                        "author": book.get("author"),
                        "book_type": book.get("book_type"),
                        "literary_genre": book.get("literary_genre"),
                        "publishing_year": book.get("publishing_year"),
                        "original_year": book.get("original_year"),
                        "tags": book.get("tags", []),
                        "language": book.get("language")
                    }
            r["copy_status"] = copy.get("status")

        r["book_info"] = book_info
        results.append(r)

    return jsonify(results), 200

# -------------------------------
# POST: Add a new reservation (reader only)
# -------------------------------
@reservations_bp.route("/reservations", methods=["POST"])
@authorize(["reader"])
def add_reservation():
    """
    Create a new reservation for a specific copy (reader)
    ---
    tags:
      - Reservations
    security:
      - Bearer: []
    summary: Reserve a specific copy
    description: |
      Readers can reserve a copy by providing its **copy_id** in the input box below.  
      - If the copy is **available**, it becomes **reserved**.  
      - If already **reserved** or **taken**, your reservation is added to the queue.  
    parameters:
      - name: copy_id
        in: query
        type: integer
        required: true
        description: The ID of the copy to reserve.
        example: 6
    responses:
      201:
        description: Reservation successfully created
      400:
        description: Copy not found or invalid
    """
    user = getattr(request, "user", None)
    try:
        user_id = int(user["user_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID"}), 400

    copy_id = request.args.get("copy_id", type=int)
    if not copy_id:
        return jsonify({"error": "copy_id is required"}), 400

    copy = db.copies.find_one({"_id": copy_id})
    if not copy:
        return jsonify({"error": "Copy not found"}), 404

    # Prevent duplicate reservations for same copy and user
    existing = db.reservations.find_one({"user_id": user_id, "copy_id": copy_id})
    if existing:
        return jsonify({"error": "You have already reserved this copy"}), 400

    # Determine queue position
    current_queue = list(db.reservations.find({"copy_id": copy_id}))
    position = len(current_queue) + 1

    # Generate numeric _id like your JSON (keeps consistency)
    last_res = db.reservations.find_one(sort=[("_id", -1)])
    new_id = (last_res["_id"] + 1) if last_res and isinstance(last_res["_id"], int) else 1

    # Timestamp with no microseconds to match existing format: "YYYY-MM-DDTHH:MM:SSZ"
    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    reservation_doc = {
        "_id": int(new_id),
        "copy_id": int(copy_id),
        "user_id": int(user_id),
        "branch_id": int(copy.get("branch_id")),
        "reservation_date": ts,
        "position_in_queue": int(position),
    }

    result = db.reservations.insert_one(reservation_doc)
    if not result.inserted_id:
        return jsonify({"error": "Failed to create reservation"}), 500

    # Update copy status only if it was "available"
    if copy.get("status") == "available":
        db.copies.update_one({"_id": copy_id}, {"$set": {"status": "reserved"}})

    return jsonify({
        "message": "Reservation created successfully",
        "reservation_id": new_id,
        "copy_id": copy_id,
        "position_in_queue": position,
        "reservation_date": ts,
        "copy_status": "reserved" if copy.get("status") == "available" else copy.get("status")
    }), 201



@reservations_bp.route("/reservations/<reservation_id>", methods=["DELETE"])
@authorize(["reader"])
def delete_reservation(reservation_id):
    """
    Cancel a reservation (reader)
    ---
    tags:
      - Reservations
    security:
      - Bearer: []
    summary: Cancel an existing reservation
    description: |
      Allows a **reader** to cancel one of their active reservations by its ID.  
      Only the user who created the reservation can delete it.  

      When a reservation is cancelled:
        - It is removed from the `reservations` collection.  
        - The queue positions of other readers waiting for the same copy are automatically updated.  
        - If this was the last reservation for a copy and the copy was marked as *reserved*, its status is changed back to *available*.
    parameters:
      - name: reservation_id
        in: path
        required: true
        type: integer
        description: ID of the reservation to cancel
    responses:
      200:
        description: Reservation successfully deleted
      404:
        description: Reservation not found
    """
    user = getattr(request, "user", None)
    try:
        user_id = int(user["user_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID"}), 400

    # Convert reservation_id to int if possible
    try:
        res_id = int(reservation_id)
    except ValueError:
        res_id = reservation_id  # fallback, in case it's not numeric

    # Find reservation belonging to this user
    res = db.reservations.find_one({"_id": res_id, "user_id": user_id})
    if not res:
        return jsonify({"error": "Reservation not found"}), 404

    copy_id = int(res["copy_id"])

    # Delete the reservation
    db.reservations.delete_one({"_id": res_id})

    # Reorder queue positions for remaining reservations for this copy
    remaining = list(db.reservations.find({"copy_id": copy_id}).sort("position_in_queue", 1))
    for i, r in enumerate(remaining, start=1):
        db.reservations.update_one({"_id": r["_id"]}, {"$set": {"position_in_queue": i}})

    # If this was the last reservation and copy isn't "taken", make it available again
    copy = db.copies.find_one({"_id": copy_id})
    if copy and copy.get("status") == "reserved" and not remaining:
        db.copies.update_one({"_id": copy_id}, {"$set": {"status": "available"}})

    return jsonify({
        "message": "Reservation cancelled successfully",
        "reservation_id": res_id,
        "copy_id": copy_id
    }), 200
