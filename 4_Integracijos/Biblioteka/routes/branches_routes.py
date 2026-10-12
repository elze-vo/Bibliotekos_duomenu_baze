from flask import Blueprint, jsonify, request
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize
from Biblioteka.utils.cassandra_logger import log_system_event

branches_bp = Blueprint("branches", __name__)

# -------------------------------
# GET: Return only branch name and ID
# -------------------------------
@branches_bp.route("/branches", methods=["GET"])
@authorize(["reader", "admin"])
def get_branches():
    """
    Get branch IDs and names (admin & reader)
    ---
    tags:
      - Branches
    security:
      - Bearer: []
    summary: Get all library branches (ID and name only)
    description: |
      Readers and admins can view all branches.  
      Each branch entry contains only its **ID** and **name**.
    responses:
      200:
        description: Returns list of branches with only _id and name
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: integer
                    example: 21
                  name:
                    type: string
                    example: "Panevėžio miesto viešoji biblioteka"
    """
    user_id = (
        f"{request.user.get('role')}_{request.user.get('user_id')}"
        if getattr(request, "user", None)
        else "unknown"
    )

    branches = list(db.branches.find({}, {"_id": 1, "name": 1}))
    results = [{"_id": int(b["_id"]), "name": b["name"]} for b in branches]

    log_system_event(
        user_id=user_id,
        event_type="access",
        entity_type="branches",
        entity_id="get_branches",
        details=f"Retrieved {len(results)} branches"
    )

    return jsonify(results), 200