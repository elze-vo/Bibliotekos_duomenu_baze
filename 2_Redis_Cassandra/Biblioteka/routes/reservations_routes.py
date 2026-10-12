from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize
from Biblioteka.utils.cache import delete_cache, redis_client
from Biblioteka.utils.cassandra_logger import log_system_event, log_book_action
from datetime import datetime

reservations_bp = Blueprint("reservations", __name__)

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
      409:
        description: Copy is currently being reserved by someone else
    """
    user = getattr(request, "user", None)

    try:
        user_id = int(user["user_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID"}), 400

    copy_id = request.args.get("copy_id", type=int)
    if not copy_id:
        return jsonify({"error": "copy_id is required"}), 400

    lock_key = f"lock:copy:{copy_id}"
    lock = redis_client.lock(lock_key, timeout=5)
    have_lock = lock.acquire(blocking=True, blocking_timeout=3)
    if not have_lock:
        return jsonify({"error": "Copy is currently being reserved by someone else. Try again."}), 409

    try:
        copy = db.copies.find_one({"_id": copy_id})
        if not copy:
            return jsonify({"error": "Copy not found"}), 404
        
        existing = db.reservations.find_one({"user_id": user_id, "copy_id": copy_id})
        if existing:
            return jsonify({"error": "You have already reserved this copy"}), 400

        current_queue = list(db.reservations.find({"copy_id": copy_id}))
        position = len(current_queue) + 1

        last_res = db.reservations.find_one(sort=[("_id", -1)])
        new_id = (last_res["_id"] + 1) if last_res and isinstance(last_res["_id"], int) else 1

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

        if copy.get("status") == "available":
            db.copies.update_one({"_id": copy_id}, {"$set": {"status": "reserved"}})

        delete_cache("book_availability_summary")

        user_id = (
          f"{request.user.get('role')}_{request.user.get('user_id')}"
          if getattr(request, "user", None)
          else "unknown"
        )
        
        log_system_event(
            user_id=user_id,
            event_type="reservation_created",
            entity_type="reservations",
            entity_id="add_reservation",
            details=f"Reserved copy {copy_id} at position {position} in queue"
        )

        book = db.books.find_one({"_id": copy["book_id"]})
        book_title = book.get("title", "Unknown Title") if book else "Unknown Title"

        log_book_action(
            user_id=f"{user_id}",
            book_id=str(copy["book_id"]),
            copy_id=str(copy_id),
            action_type="reserved",
            book_title=book_title,
            details=f"Reserved copy {copy_id} at position {position} in queue"
        )


    finally:
        lock.release()

    return jsonify({
        "message": "Reservation created successfully",
        "reservation_id": new_id,
        "copy_id": copy_id,
        "position_in_queue": position,
        "reservation_date": ts,
        "copy_status": "reserved" if copy.get("status") == "available" else copy.get("status")
    }), 201

# -------------------------------
# DELETE: Cancel a reservation (reader)
# -------------------------------
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

    try:
        res_id = int(reservation_id)
    except ValueError:
        res_id = reservation_id

    res = db.reservations.find_one({"_id": res_id, "user_id": user_id})
    if not res:
        return jsonify({"error": "Reservation not found"}), 404

    copy_id = int(res["copy_id"])

    db.reservations.delete_one({"_id": res_id})

    remaining = list(db.reservations.find({"copy_id": copy_id}).sort("position_in_queue", 1))
    for i, r in enumerate(remaining, start=1):
        db.reservations.update_one({"_id": r["_id"]}, {"$set": {"position_in_queue": i}})

    copy = db.copies.find_one({"_id": copy_id})
    if copy and copy.get("status") == "reserved" and not remaining:
        db.copies.update_one({"_id": copy_id}, {"$set": {"status": "available"}})

    delete_cache("book_availability_summary")

    user_id = (
        f"{request.user.get('role')}_{request.user.get('user_id')}"
        if getattr(request, "user", None)
        else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="reservation_cancelled",
        entity_type="reservations",
        entity_id="delete_reservation",
        details=f"Cancelled reservation for copy {copy_id}, remaining queue length: {len(remaining)}"
    )

    book = db.books.find_one({"_id": copy["book_id"]})
    book_title = book.get("title", "Unknown Title") if book else "Unknown Title"


    log_book_action(
        user_id=f"{user_id}",
        book_id=str(copy["book_id"]),
        copy_id=str(copy_id),
        action_type="reservation_cancelled",
        book_title=book_title,
        details=f"Cancelled reservation for copy {copy_id}, remaining queue length: {len(remaining)}"
    )


    return jsonify({
        "message": "Reservation cancelled successfully",
        "reservation_id": res_id,
        "copy_id": copy_id
    }), 200
