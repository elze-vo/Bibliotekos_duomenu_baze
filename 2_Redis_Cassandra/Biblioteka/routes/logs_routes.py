from flask import Blueprint, jsonify, request
from datetime import date, datetime
from cassandra.util import Date
from Biblioteka.utils.cassandra_conn import get_cassandra_session
from Biblioteka.utils.auth import authorize


logs_bp = Blueprint("logs", __name__, url_prefix="/logs")
session = get_cassandra_session()


# -----------------------------
# CREATE TABLE FUNCTIONS
# -----------------------------
def create_tables():
    session.execute("""
        CREATE TABLE IF NOT EXISTS system_events_by_date (
            event_date date,
            event_time timestamp,
            user_id text,
            event_type text,
            entity_type text,
            entity_id text,
            details text,
            PRIMARY KEY (event_date, event_time, user_id)
        );
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS system_events_by_user (
            user_id text,
            event_time timestamp,
            event_type text,
            entity_type text,
            entity_id text,
            details text,
            PRIMARY KEY (user_id, event_time)
        );
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS book_actions_by_user (
            user_id text,
            action_time timestamp,
            action_type text,
            book_id text,
            copy_id text,
            book_title text,
            details text,
            PRIMARY KEY (user_id, action_time)
        );
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS book_actions_by_book (
            book_id text,
            action_time timestamp,
            action_type text, 
            copy_id text,
            user_id text,
            book_title text,
            details text,
            PRIMARY KEY (book_id, action_time)
        );
    """)
    print("[CASSANDRA] All tables created successfully.")


# -----------------------------
# ROUTES (Admin-only)
# -----------------------------

@logs_bp.route("/init_tables", methods=["POST"])
@authorize(["admin"])
def initialize_tables():
    """
    Logs: Initialize Cassandra log tables (admin)
    ---
    tags:
      - Logs
    security:
      - Bearer: []
    summary: Create all Cassandra tables for system and book event logs
    description: Admin-only endpoint that initializes all four log tables in Cassandra if they do not exist.
    responses:
      200:
        description: Confirmation that all Cassandra log tables were created successfully
    """
    create_tables()
    return jsonify({"message": "All Cassandra tables created successfully."})


@logs_bp.route("/system_events/by_date", methods=["GET"])
@authorize(["admin"])
def get_system_events_by_date():
    """
    Logs: View all system events grouped by date (admin)
    ---
    tags:
      - Logs
    security:
      - Bearer: []
    summary: Retrieve all system events ordered by event date
    description: Returns all records from the `system_events_by_date` table. Accessible only to administrators.
    responses:
      200:
        description: A list of system events with date, user, and event details
    """
    rows = session.execute("SELECT * FROM system_events_by_date;")

    def serialize_value(value):
        if isinstance(value, (datetime, date, Date)):
            return str(value)
        return value

    serialized_rows = []
    for row in rows:
        serialized_row = {k: serialize_value(v) for k, v in row._asdict().items()}
        serialized_rows.append(serialized_row)

    return jsonify(serialized_rows)



@logs_bp.route("/system_events/by_user", methods=["GET"])
@authorize(["admin"])
def get_system_events_by_user():
    """
    Logs: View all system events grouped by user (admin)
    ---
    tags:
      - Logs
    security:
      - Bearer: []
    summary: Retrieve all system events ordered by user
    description: Returns all records from the `system_events_by_user` table. Accessible only to administrators.
    responses:
      200:
        description: A list of system events categorized by user
    """
    rows = session.execute("SELECT * FROM system_events_by_user;")
    return jsonify([dict(row._asdict()) for row in rows])

def serialize_row(row):
    """Convert Cassandra rows into JSON-safe dictionaries."""
    def convert(v):
        if isinstance(v, (datetime, date, Date)):
            return str(v)
        return v
    return {k: convert(v) for k, v in row._asdict().items()}


@logs_bp.route("/book_actions/by_user", methods=["GET"])
@authorize(["admin"])
def get_book_actions_by_user():
    """
    Logs: View all book actions by a specific user (admin)
    ---
    tags:
      - Logs
    security:
      - Bearer: []
    summary: Retrieve book actions performed by a specific user
    description: Returns all records from the `book_actions_by_user` table for the specified user ID. Accessible only to administrators.
    parameters:
      - name: user_id
        in: query
        type: string
        required: true
        description: The ID of the user whose book actions to retrieve.
    responses:
      200:
        description: A list of all user-related book actions (borrowed, returned, etc.)
      400:
        description: Missing required query parameter `user_id`
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    query = "SELECT * FROM book_actions_by_user WHERE user_id = %s;"
    rows = session.execute(query, [user_id])

    return jsonify([serialize_row(row) for row in rows])


@logs_bp.route("/book_actions/by_book", methods=["GET"])
@authorize(["admin"])
def get_book_actions_by_book():
    """
    Logs: View all book actions for a specific book (admin)
    ---
    tags:
      - Logs
    security:
      - Bearer: []
    summary: Retrieve all actions performed on a specific book
    description: Returns all records from the `book_actions_by_book` table for the specified book ID (ISBN). Accessible only to administrators.
    parameters:
      - name: book_id
        in: query
        type: string
        required: true
        description: The book ID (ISBN) to search for.
    responses:
      200:
        description: A list of book-related actions (borrowed, returned, reserved, etc.)
      400:
        description: Missing required query parameter `book_id`
    """
    book_id = request.args.get("book_id")
    if not book_id:
        return jsonify({"error": "Missing required parameter: book_id"}), 400

    query = "SELECT * FROM book_actions_by_book WHERE book_id = %s;"
    rows = session.execute(query, [book_id])

    return jsonify([serialize_row(row) for row in rows])

