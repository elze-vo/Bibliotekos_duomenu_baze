from flask import Blueprint, jsonify
from Biblioteka.db import db
from Biblioteka.utils.auth import authorize

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
    branches = list(db.branches.find({}, {"_id": 1, "name": 1}))
    results = [{"_id": int(b["_id"]), "name": b["name"]} for b in branches]
    return jsonify(results), 200
