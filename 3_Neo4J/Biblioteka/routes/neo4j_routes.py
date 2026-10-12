from flask import Blueprint, jsonify, request
from Biblioteka.utils.auth import authorize
from Biblioteka.utils.mongo_conn import get_mongo_db
from Biblioteka.utils.neo4j_sync import get_all_user_ids, sync_user_reads, sync_books
from Biblioteka.utils.neo4j_recommendations import (
    recommend_books_from_similar_users_unlimited,
    recommend_books_from_similar_genres_unlimited,
    recommend_books_from_similar_users_limited,
    recommend_books_from_similar_genres_limited
)

neo4j_bp = Blueprint("neo4j", __name__, url_prefix="/neo4j")
db = get_mongo_db()


def _sync_data():
    """Helper: Sync reads and books from MongoDB to Neo4j."""
    all_user_ids = get_all_user_ids()
    sync_user_reads(all_user_ids)
    sync_books()


# ------------------- Unlimited Depth ------------------- #

@neo4j_bp.route("/recommend/users/unlimited", methods=["GET"])
@authorize(["reader"])
def recommend_users_unlimited():
    """
    Recommend books based on similar users (unlimited depth).
    ---
    tags:
      - Neo4J
    security:
      - Bearer: []
    summary: Recommend books from similar users, unlimited-depth
    responses:
      200:
        description: A list of recommended books
    """
    user_id = request.user["user_id"]
    _sync_data()
    recs = recommend_books_from_similar_users_unlimited(f"reader_{user_id}")
    return jsonify({"recommendations": recs})


@neo4j_bp.route("/recommend/genres/unlimited", methods=["GET"])
@authorize(["reader"])
def recommend_genres_unlimited():
    """
    Recommend books based on similar genres (unlimited depth).
    ---
    tags:
      - Neo4J
    security:
      - Bearer: []
    summary: Recommend books from similar genres, unlimited-depth
    responses:
      200:
        description: A list of recommended books
    """
    user_id = request.user["user_id"]
    _sync_data()
    recs = recommend_books_from_similar_genres_unlimited(f"reader_{user_id}")
    return jsonify({"recommendations": recs})


# ------------------- Limited Depth ------------------- #

@neo4j_bp.route("/recommend/users/limited", methods=["GET"])
@authorize(["reader"])
def recommend_users_limited():
    """
    Recommend books based on similar users (shallow / limited depth).
    ---
    tags:
      - Neo4J
    security:
      - Bearer: []
    summary: Recommend books from similar users, limited-depth
    responses:
      200:
        description: A list of recommended books
    """
    user_id = request.user["user_id"]
    _sync_data()
    recs = recommend_books_from_similar_users_limited(f"reader_{user_id}")
    return jsonify({"recommendations": recs})


@neo4j_bp.route("/recommend/genres/limited", methods=["GET"])
@authorize(["reader"])
def recommend_genres_limited():
    """
    Recommend books based on similar genres (shallow / limited depth).
    ---
    tags:
      - Neo4J
    security:
      - Bearer: []
    summary: Recommend books from similar genres, limited-depth
    responses:
      200:
        description: A list of recommended books
    """
    user_id = request.user["user_id"]
    _sync_data()
    recs = recommend_books_from_similar_genres_limited(f"reader_{user_id}")
    return jsonify({"recommendations": recs})
