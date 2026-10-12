from flask import request, jsonify
from functools import wraps
import jwt
import datetime
from Biblioteka.config import JWT_KEY


def create_token(user_id, role, extra_claims=None):
    """
    Create a JWT token with optional extra claims (e.g. branch_id for admins).
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4)
    }

    # Include extra claims if provided
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, JWT_KEY, algorithm="HS256")


def authorize(roles):
    """
    Decorator that checks for a valid JWT token and required roles.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization")
            if not token:
                return jsonify({"error": "Missing token"}), 403

            if token.startswith("Bearer "):
                token = token.split(" ", 1)[1]

            try:
                decoded = jwt.decode(token, JWT_KEY, algorithms=["HS256"])
            except Exception:
                return jsonify({"error": "Invalid or expired token"}), 403

            if decoded.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403

            # Attach decoded token to request for route usage
            request.user = decoded
            return f(*args, **kwargs)
        return wrapper
    return decorator
