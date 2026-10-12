from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize

copies_bp = Blueprint("copies", __name__)

def serialize_id(doc):
    """Convert Mongo _id to int for JSON responses."""
    if "_id" in doc:
        doc["_id"] = int(doc["_id"])
    return doc


# -------------------------------
# GET: Readers & Admins can view copies
# -------------------------------
@copies_bp.route("/copies", methods=["GET"])
@authorize(["reader", "admin"])
def get_copies():
    """
    Get copies (admin & reader)
    ---
    tags:
      - Copies
    security:
      - Bearer: []
    summary: View copies of books
    description: |
      **Reader:** Can filter available and reserved copies by `book_id` and `branch_id`.  
      **Admin:** Can only see **all copies from their own branch**, no filters allowed.
    parameters:
      - name: book_id
        in: query
        type: string
        required: false
        description: (Reader only) Filter copies by book ID
        example: "9780000000022"
      - name: branch_id
        in: query
        type: integer
        required: false
        description: (Reader only) Filter copies by branch ID
        example: 21
    responses:
      200:
        description: Returns filtered copies
    """
    user = getattr(request, "user", None)
    role = user.get("role")
    query = {}

    # --------------------------
    # Reader functionality
    # --------------------------
    if role == "reader":
        # Optional filter by book_id
        book_id = request.args.get("book_id")
        if book_id:
            query["book_id"] = book_id

        # Optional filter by branch_id
        branch_id = request.args.get("branch_id", type=int)
        if branch_id:
            branch = db.branches.find_one({"_id": branch_id})
            if not branch:
                return jsonify({"error": f"No branch found with ID {branch_id}"}), 404
            query["branch_id"] = branch_id

        # Readers can only see available or reserved
        query["status"] = {"$in": ["available", "reserved"]}

    # --------------------------
    # Admin functionality
    # --------------------------
    elif role == "admin":
        admin_branch_id = int(user.get("branch_id"))
        query["branch_id"] = admin_branch_id

    # --------------------------
    # Fetch and return
    # --------------------------
    copies = [serialize_id(c) for c in db.copies.find(query)]
    return jsonify({"results": copies}), 200



# -------------------------------
# POST: Admin adds new copy — only to their branch
# -------------------------------
@copies_bp.route("/copies", methods=["POST"])
@authorize(["admin"])
def add_copy():
    """
    Add a new copy (admin)
    ---
    tags:
      - Copies
    security:
      - Bearer: []
    consumes:
      - application/json
    summary: Add a new copy to your branch
    description: |
      Admins can create a new copy of a book **only for their own branch**.  
      The copy's **status** will automatically be set to `"available"`.
      The `book_id` must exist in the `books` collection.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - book_id
          properties:
            book_id:
              type: string
              description: Must match an existing `_id` in `books.json`
              example: "9780000000028"
    responses:
      201:
        description: Copy successfully added
      400:
        description: Invalid data or unauthorized branch
    """
    user = getattr(request, "user", None)
    admin_branch_id = int(user.get("branch_id"))  # branch tied to the logged in admin

    data = request.get_json() or {}
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id is required"}), 400

    # Check if book exists
    book_exists = db.books.find_one({"_id": str(book_id)})
    if not book_exists:
        return jsonify({"error": f"No book found with ID {book_id}"}), 404

    # Create new copy for admin's branch
    last_copy = db.copies.find_one(sort=[("_id", -1)])
    new_id = (last_copy["_id"] + 1) if last_copy else 1

    new_copy = {
        "_id": new_id,
        "book_id": str(book_id),
        "branch_id": admin_branch_id,
        "status": "available"
    }

    db.copies.insert_one(new_copy)
    return jsonify({
        "message": "Copy added successfully",
        "copy": new_copy
    }), 201


# -------------------------------
# DELETE: Admin deletes copies only from their branch
# -------------------------------
@copies_bp.route("/copies/<int:copy_id>", methods=["DELETE"])
@authorize(["admin"])
def delete_copy(copy_id):
    """
    Delete a copy (admin)
    ---
    tags:
      - Copies
    security:
      - Bearer: []
    summary: Delete a copy (restricted to admin's branch)
    description: |
      Allows an **admin** to delete a specific copy of a book, but only if it belongs to **their own branch**.  
      This restriction ensures that administrators cannot modify or delete copies managed by other branches.
    parameters:
      - name: copy_id
        in: path
        required: true
        type: integer
        description: ID of the copy to delete (must belong to your branch)
    responses:
      200:
        description: Copy deleted successfully
      403:
        description: Admin cannot delete copies outside their branch
      404:
        description: Copy not found
    """
    user = getattr(request, "user", None)
    admin_branch_id = int(user.get("branch_id"))

    copy = db.copies.find_one({"_id": copy_id})
    if not copy:
        return jsonify({"error": "Copy not found"}), 404

    # Make sure the copy belongs to the admin's branch
    if int(copy["branch_id"]) != admin_branch_id:
        return jsonify({"error": "You can only delete copies from your own branch"}), 403

    db.copies.delete_one({"_id": copy_id})
    return jsonify({"message": f"Copy {copy_id} deleted successfully"}), 200


@copies_bp.route("/copies/take", methods=["POST"])
@authorize(["admin"])
def take_copy():
    """
    Mark a copy as taken by a user (admin)
    ---
    tags:
      - Copies
    security:
      - Bearer: []
    summary: Mark a copy as taken by a user
    description: |
      Admins can mark a copy as **taken** for a specific user, but:
      - They can only manage copies in their own branch.
      - If the copy is reserved, only the **first in queue** can take it.
      - If available, anyone can take it.
      - If already taken, an error is returned.
    parameters:
      - name: copy_id
        in: query
        required: true
        type: integer
        description: The ID of the copy to mark as taken
        example: 52
      - name: user_id
        in: query
        required: true
        type: integer
        description: The ID of the user taking the copy
        example: 873
    responses:
      200:
        description: Copy successfully marked as taken
      400:
        description: Invalid input or not first in queue
      403:
        description: Admin cannot modify copies outside their branch
      404:
        description: Copy not found
    """
    user = getattr(request, "user", None)
    admin_branch_id = int(user.get("branch_id"))

    copy_id = request.args.get("copy_id", type=int)
    user_id = request.args.get("user_id", type=int)

    if copy_id is None or user_id is None:
        return jsonify({"error": "copy_id and user_id are required"}), 400

    # --- Validate copy ---
    copy = db.copies.find_one({"_id": copy_id})
    if not copy:
        return jsonify({"error": f"Copy with ID {copy_id} not found"}), 404

    # --- Ensure same branch ---
    if int(copy["branch_id"]) != admin_branch_id:
        return jsonify({"error": "You can only modify copies from your branch"}), 403

    # --- Check status ---
    if copy["status"] == "taken":
        return jsonify({"error": "This copy is already taken"}), 400

    # --- Handle reservation ---
    if copy["status"] == "reserved":
        first_res = db.reservations.find_one(
            {"copy_id": copy_id},
            sort=[("position_in_queue", 1)]
        )
        if not first_res or first_res["user_id"] != user_id:
            return jsonify({"error": "User is not first in the reservation queue"}), 400

        # remove reservation and shift queue
        db.reservations.delete_one({"_id": first_res["_id"]})
        remaining = list(db.reservations.find({"copy_id": copy_id}).sort("position_in_queue", 1))
        for idx, res in enumerate(remaining, start=1):
            db.reservations.update_one({"_id": res["_id"]}, {"$set": {"position_in_queue": idx}})

    # --- Update copy ---
    due_date = (datetime.utcnow() + timedelta(days=30)).replace(microsecond=0).isoformat() + "Z"
    db.copies.update_one(
        {"_id": copy_id},
        {"$set": {"status": "taken", "taker_id": user_id, "due_date": due_date}}
    )

    return jsonify({
        "message": f"Copy {copy_id} is now taken by user {user_id}",
        "copy_id": copy_id,
        "taker_id": user_id,
        "due_date": due_date
    }), 200


# -------------------------------
# POST: Admin returns a taken copy
# -------------------------------
@copies_bp.route("/copies/return", methods=["POST"])
@authorize(["admin"])
def return_copy():
    """
    Return a taken copy (admin)
    ---
    tags:
      - Copies
    security:
      - Bearer: []
    summary: Return a taken copy to the branch
    description: |
      Admins can **return** a taken copy from their branch.
      - If the copy has no reservations → status becomes **`available`**.
      - If there are active reservations → status becomes **`reserved`**.
      - The `taker_id` and `due_date` fields are removed.
    parameters:
      - name: copy_id
        in: query
        required: true
        type: integer
        description: ID of the copy to return
        example: 52
    responses:
      200:
        description: Copy successfully returned
      400:
        description: Copy is not taken
      403:
        description: Admin cannot return copies from other branches
      404:
        description: Copy not found
    """
    user = getattr(request, "user", None)
    admin_branch_id = int(user.get("branch_id"))

    copy_id = request.args.get("copy_id", type=int)
    if copy_id is None:
        return jsonify({"error": "copy_id is required"}), 400

    # --- Validate copy ---
    copy = db.copies.find_one({"_id": copy_id})
    if not copy:
        return jsonify({"error": f"Copy with ID {copy_id} not found"}), 404

    # --- Check branch ownership ---
    if int(copy["branch_id"]) != admin_branch_id:
        return jsonify({"error": "You can only return copies from your own branch"}), 403

    # --- Must be taken ---
    if copy.get("status") != "taken":
        return jsonify({"error": "This copy is not currently taken"}), 400

    # --- Check if there are reservations ---
    has_reservations = db.reservations.find_one({"copy_id": copy_id}) is not None
    new_status = "reserved" if has_reservations else "available"

    # --- Update copy ---
    db.copies.update_one(
        {"_id": copy_id},
        {"$set": {"status": new_status},
         "$unset": {"taker_id": "", "due_date": ""}}
    )

    return jsonify({
        "message": f"Copy {copy_id} successfully returned and marked as '{new_status}'",
        "copy_id": copy_id,
        "new_status": new_status
    }), 200
