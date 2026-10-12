from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import create_token
from Biblioteka.utils.security import check_password
from Biblioteka.utils.cassandra_logger import log_system_event

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login as reader or admin
    --- 
    tags:
      - Authentication
    summary: Login as reader or admin
    description: |
      Use this endpoint to log in as either a **reader** or an **admin**.

      ### Reader example
      ```json
      {
        "username": "laura.urboniene@pastas.lt",
        "password": "laura123"
      }
      ```

      ### Admin example
      ```json
      {
        "username": "vilnius1",
        "password": "vilnius1"
      }
      ```
    consumes:
      - application/json
    parameters:
      - in: body
        name: credentials
        description: Reader (email/password) or Admin (username/password)
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Reader email or admin username
              example: "reader@example.com"
            password:
              type: string
              example: "password123"
    responses:
      200:
        description: Successfully logged in
        schema:
          type: object
          properties:
            token:
              type: string
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            role:
              type: string
              enum: [reader, admin]
              example: "reader"
            user_id:
              type: string
              example: "1"
      400:
        description: Invalid credentials or missing fields
      415:
        description: Request must be JSON
    """
    if not request.is_json:
        log_system_event(
            user_id="unknown",
            event_type="login_failed",
            entity_type="auth",
            entity_id="login",
            details="Request not JSON"
        )
        return jsonify({"error": "Request must be JSON"}), 415

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        log_system_event(
            user_id="unknown",
            event_type="login_failed",
            entity_type="auth",
            entity_id="login",
            details="Missing username or password"
        )
        return jsonify({"error": "Missing username or password"}), 400

    # --------------------------
    # Reader login
    # --------------------------
    user = db.users.find_one({"email": username})
    if user and check_password(password, user.get("password", "")):
        token = create_token(str(user["_id"]), "reader")
        
        log_system_event(
            user_id=f"reader_{user['_id']}",
            event_type="login_success",
            entity_type="auth",
            entity_id="reader_login",
            details=f"Reader '{username}' logged in successfully"
        )
        return jsonify({
            "token": token,
            "role": "reader",
            "user_id": str(user["_id"])
        }), 200

    # --------------------------
    # Admin login
    # --------------------------
    branch = db.branches.find_one({"login.username": username})
    if branch and check_password(password, branch.get("login", {}).get("password", "")):
        token = create_token(
            user_id=str(branch["_id"]),
            role="admin",
            extra_claims={"branch_id": str(branch["_id"])}
        )

        log_system_event(
            user_id=f"admin_{branch['_id']}",
            event_type="login_success",
            entity_type="auth",
            entity_id="admin_login",
            details=f"Admin '{username}' logged in successfully"
        )
        return jsonify({
            "token": token,
            "role": "admin",
            "branch_id": str(branch["_id"])
        }), 200

    # --------------------------
    # Invalid credentials
    # --------------------------
    log_system_event(
        user_id="unknown",
        event_type="login_failed",
        entity_type="auth",
        entity_id="login",
        details=f"Invalid login attempt for username '{username}'"
    )

    return jsonify({"error": "Invalid username or password"}), 400