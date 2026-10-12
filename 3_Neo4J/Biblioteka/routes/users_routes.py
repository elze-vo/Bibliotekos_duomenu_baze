from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize
from Biblioteka.utils.security import hash_password
from Biblioteka.utils.cassandra_logger import log_system_event
import re

users_bp = Blueprint("users", __name__)

def serialize_id(doc):
    if "_id" in doc:
        doc["_id"] = int(doc["_id"])
    return doc


# -------------------------------
# GET: List or search users (admin)
# -------------------------------
@users_bp.route("/users", methods=["GET"])
@authorize(["admin"])
def get_users():
    """
    Get or search users (admin)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    summary: List all users or search by fields
    description: |
      Returns a list of users, sorted by `_id` ascending.  
      Admins can also search by specific fields.

      Supported query params:
      - `id` → exact match on user ID
      - `first_name` → partial, case-insensitive
      - `last_name` → partial, case-insensitive
      - `email` → partial, case-insensitive
      - `phone` → partial, case-insensitive
    parameters:
      - name: id
        in: query
        type: integer
        required: false
        description: Search by exact user ID
        example: 1
      - name: first_name
        in: query
        type: string
        required: false
        description: Search by first name (partial, case-insensitive)
        example: "Laura"
      - name: last_name
        in: query
        type: string
        required: false
        description: Search by last name (partial, case-insensitive)
        example: "Urbonienė"
      - name: email
        in: query
        type: string
        required: false
        description: Search by email (partial, case-insensitive)
        example: "laura.urboniene@pastas.lt"
      - name: phone
        in: query
        type: string
        required: false
        description: Search by phone (partial, case-insensitive)
        example: "+37067990886"
    responses:
      200:
        description: A list of user objects
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: integer
                    example: 1
                  first_name:
                    type: string
                    example: "Laura"
                  last_name:
                    type: string
                    example: "Urbonienė"
                  email:
                    type: string
                    example: "laura.urboniene@pastas.lt"
                  phone:
                    type: string
                    example: "+37067990886"
                  address:
                    type: string
                    example: "Utena, Žalioji g. 309, Lietuva"
    """
    query = {}
    user_id = request.args.get("id", type=int)
    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")
    email = request.args.get("email")
    phone = request.args.get("phone")

    if user_id is not None:
        query["_id"] = user_id
    if first_name:
        query["first_name"] = {"$regex": re.escape(first_name), "$options": "i"}
    if last_name:
        query["last_name"] = {"$regex": re.escape(last_name), "$options": "i"}
    if email:
        query["email"] = {"$regex": re.escape(email), "$options": "i"}
    if phone:
        query["phone"] = {"$regex": re.escape(phone), "$options": "i"}

    users = [serialize_id(u) for u in db.users.find(query).sort("_id", 1)]

    user_id = (
        f"{request.user.get('role')}_{request.user.get('user_id')}"
        if getattr(request, "user", None)
        else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="read",
        entity_type="users",
        entity_id="get_users",
        details=f"Admin viewed list of users with filters: {query}"
    )

    return jsonify(users), 200

# -------------------------------
# POST: Add a new user
# -------------------------------
@users_bp.route("/users", methods=["POST"])
@authorize(["admin"])
def add_user():
    """
    Add a new user (admin)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    summary: Add a new user
    description: |
      Allows an **admin** to create a new user account in the system. 

      The system automatically assigns a unique, incrementing `_id` value for the new user.

      **Required fields:**
        - `first_name`
        - `last_name`
        - `address`
        - `phone`
        - `email`
        - `password`
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            first_name:
              type: string
              example: "Jonas"
            last_name:
              type: string
              example: "Kazlauskas"
            address:
              type: string
              example: "Vilnius, Gedimino pr. 10"
            phone:
              type: string
              example: "+37061234567"
            email:
              type: string
              example: "jonas@example.com"
            password:
              type: string
              example: "jonas123"
    responses:
      201:
        description: User added successfully
    """
    data = request.get_json() or {}
    required_fields = ["first_name", "last_name", "address", "phone", "email", "password"]
    if not all(f in data for f in required_fields):
        return jsonify({"error": "Missing required user fields"}), 400

    last_user = db.users.find_one(sort=[("_id", -1)])
    new_id = (last_user["_id"] + 1) if last_user else 1

    hashed_password = hash_password(data["password"])

    user_doc = {
        "_id": new_id,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "address": data["address"],
        "phone": data["phone"],
        "email": data["email"],
        "password": hashed_password,
    }

    db.users.insert_one(user_doc)
    user_doc_copy = user_doc.copy()
    user_doc_copy.pop("password")

    user_id = (
      f"{request.user.get('role')}_{request.user.get('user_id')}"
      if getattr(request, "user", None)
      else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="create",
        entity_type="users",
        entity_id="add_user",
        details=f"Admin added user {user_doc_copy['first_name']} {user_doc_copy['last_name']} ({user_doc_copy['email']})"
    )

    return jsonify({"message": "User added successfully", "user": user_doc_copy}), 201

# -------------------------------
# DELETE: Remove a user + cascade cleanup
# -------------------------------
@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@authorize(["admin"])
def delete_user(user_id):
    """
    Delete a user and clean related data (admin)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    summary: Delete a user and related data
    description: |
      Allows an **admin** to completely remove a user from the system. 
    parameters:
      - name: user_id
        in: path
        required: true
        type: integer
        description: ID of the user to delete
    responses:
      200:
        description: User and related data deleted successfully
      404:
        description: User not found
    """
    user = db.users.find_one({"_id": user_id})
    if not user:
        return jsonify({"error": f"User {user_id} not found"}), 404

    reservations = list(db.reservations.find({"user_id": user_id}))
    for r in reservations:
        copy_id = r["copy_id"]
        db.reservations.delete_one({"_id": r["_id"]})

        queue = list(db.reservations.find({"copy_id": copy_id}).sort("position_in_queue", 1))
        for i, q in enumerate(queue, start=1):
            db.reservations.update_one({"_id": q["_id"]}, {"$set": {"position_in_queue": i}})

        copy = db.copies.find_one({"_id": copy_id})
        if copy:
            if not queue and copy.get("status") == "reserved":
                db.copies.update_one({"_id": copy_id}, {"$set": {"status": "available"}})
            elif queue and copy.get("status") == "taken":
                db.copies.update_one({"_id": copy_id}, {"$set": {"status": "reserved"}})

    taken_copies = list(db.copies.find({"taker_id": user_id}))
    for c in taken_copies:
        copy_id = c["_id"]
        db.copies.update_one(
            {"_id": copy_id},
            {"$unset": {"taker_id": "", "due_date": ""}}
        )

        has_res = db.reservations.find_one({"copy_id": copy_id})
        new_status = "reserved" if has_res else "available"
        db.copies.update_one({"_id": copy_id}, {"$set": {"status": new_status}})

    db.users.delete_one({"_id": user_id})

    deleted_user_id = user_id

    user_id = (
      f"{request.user.get('role')}_{request.user.get('user_id')}"
      if getattr(request, "user", None)
      else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="delete",
        entity_type="users",
        entity_id="delete_user",
        details=f"Admin deleted user {user['first_name']} {user['last_name']} and cleaned {len(reservations)} reservations and {len(taken_copies)} taken copies"
    )

    return jsonify({
        "message": f"User {deleted_user_id} and related data deleted successfully",
        "deleted_reservations": len(reservations),
        "affected_copies": len(taken_copies)
    }), 200


# -------------------------------
# GET: Reader views their personal info
# -------------------------------
@users_bp.route("/me", methods=["GET"])
@authorize(["reader"])
def get_my_info():
    """
    Get personal information (reader)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    summary: View your personal information
    description: |
      Readers can view their own stored profile information.
      No input fields are required — the user is identified from the token.
    responses:
      200:
        description: User info retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                _id:
                  type: integer
                  example: 1
                first_name:
                  type: string
                  example: "Laura"
                last_name:
                  type: string
                  example: "Urbonienė"
                address:
                  type: string
                  example: "Utena, Žalioji g. 309, Lietuva"
                phone:
                  type: string
                  example: "+37067990886"
                email:
                  type: string
                  example: "laura.urboniene@pastas.lt"
      404:
        description: User not found
    """
    user = getattr(request, "user", None)
    user_id = int(user.get("user_id"))

    db_user = db.users.find_one({"_id": user_id})
    if not db_user:
        return jsonify({"error": "User not found"}), 404

    db_user = serialize_id(db_user)
    db_user.pop("password", None)

    user_id = (
      f"{request.user.get('role')}_{request.user.get('user_id')}"
      if getattr(request, "user", None)
      else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="read",
        entity_type="users",
        entity_id="get_my_info",
        details="Reader viewed personal information"
    )

    return jsonify(db_user), 200

# -------------------------------
# PUT: Reader updates their personal info
# -------------------------------
@users_bp.route("/me", methods=["PUT"])
@authorize(["reader"])
def update_my_info():
    """
    Update personal information (reader)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    summary: Update your personal information (except _id)
    description: |
      Readers can update their personal information:  
      - `first_name`  
      - `last_name`  
      - `address`  
      - `phone`  
      - `email`  
      - `password`  
      `_id` cannot be changed.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            first_name:
              type: string
              example: "Vardas"
            last_name:
              type: string
              example: "Pavardė"
            address:
              type: string
              example: "Miestas, Gatvė g. 1, Lietuva"
            phone:
              type: string
              example: "+37000000000"
            email:
              type: string
              example: "vardas.pavarde@pastas.lt"
            password:
              type: string
              example: "vardas123"
    responses:
      200:
        description: Personal information updated successfully
      400:
        description: No valid fields provided
      404:
        description: User not found
    """
    user = getattr(request, "user", None)
    user_id = int(user.get("user_id"))
    data = request.get_json() or {}

    allowed_fields = {"first_name", "last_name", "address", "phone", "email", "password"}
    update_fields = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

    if not update_fields:
        return jsonify({"error": "No valid fields provided to update"}), 400

    if "password" in update_fields:
        update_fields["password"] = hash_password(update_fields["password"])

    result = db.users.update_one({"_id": user_id}, {"$set": update_fields})
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404
    
    user_id = (
      f"{request.user.get('role')}_{request.user.get('user_id')}"
      if getattr(request, "user", None)
      else "unknown"
    )

    log_system_event(
        user_id=user_id,
        event_type="update",
        entity_type="users",
        entity_id="update_my_info",
        details=f"Updated fields: {', '.join(update_fields.keys())}"
    )

    return jsonify({"message": "Personal information updated successfully"}), 200