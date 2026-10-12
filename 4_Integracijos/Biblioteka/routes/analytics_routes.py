from flask import Blueprint, jsonify, request
from Biblioteka.utils.auth import authorize
from Biblioteka.utils.clickhouse_conn import get_clickhouse_client
from Biblioteka.utils.clickhouse_init import init_clickhouse_tables
from Biblioteka.utils.rebuild_clickhouse import rebuild

analytics_bp = Blueprint('analytics_bp', __name__)

@analytics_bp.get('/analytics/top-books')
@authorize(["admin"])
def top_books():
    """
    Get top 10 borrowed books.
    ---
    tags:
      - Analytics
    parameters:
      - name: from
        in: query
        type: string
        format: date-time
        required: false
        description: Start timestamp (ISO format)
      - name: to
        in: query
        type: string
        format: date-time
        required: false
        description: End timestamp (ISO format)
    responses:
      200:
        description: List of top borrowed books
        schema:
          type: array
          items:
            type: object
            properties:
              book_title:
                type: string
              book_id:
                type: string
              borrows:
                type: integer
    """
    client = get_clickhouse_client()
    from_ts = request.args.get('from')
    to_ts = request.args.get('to')

    where = "WHERE action_type = 'taken'"
    if from_ts:
        where += f" AND action_time >= toDateTime('{from_ts}')"
    if to_ts:
        where += f" AND action_time <= toDateTime('{to_ts}')"

    q = f"SELECT book_title, book_id, count() AS cnt FROM library_analytics.book_actions {where} GROUP BY book_title, book_id ORDER BY cnt DESC LIMIT 10"
    res = client.query(q).result_rows

    return jsonify([{"book_title": r[0], "book_id": r[1], "borrows": r[2]} for r in res])


@analytics_bp.get('/analytics/borrows-per-day')
@authorize(["admin"])
def borrows_per_day():
    """
    Get number of book borrows per day for the last year.
    ---
    tags:
      - Analytics
    responses:
      200:
        description: Daily borrow counts
        schema:
          type: array
          items:
            type: object
            properties:
              date:
                type: string
              count:
                type: integer
    """
    client = get_clickhouse_client()
    q = """
    SELECT toDate(action_time) AS day, count() AS cnt
    FROM library_analytics.book_actions
    WHERE action_type = 'taken'
    GROUP BY day
    ORDER BY day DESC
    LIMIT 365
    """
    res = client.query(q).result_rows
    return jsonify([{"date": str(r[0]), "count": r[1]} for r in res])


@analytics_bp.get('/analytics/active-readers')
@authorize(["admin"])
def active_readers():
    """
    Get top 50 most active readers (by number of borrows).
    ---
    tags:
      - Analytics
    responses:
      200:
        description: Active readers with borrow counts
        schema:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: string
              borrows:
                type: integer
    """
    client = get_clickhouse_client()
    q = "SELECT user_id, count() AS cnt FROM library_analytics.book_actions WHERE action_type = 'taken' GROUP BY user_id ORDER BY cnt DESC LIMIT 50"
    res = client.query(q).result_rows
    return jsonify([{"user_id": r[0], "borrows": r[1]} for r in res])


@analytics_bp.get('/analytics/init-clickhouse')
@authorize(["admin"])
def init_clickhouse():
    """
    Initialize ClickHouse database and tables.
    ---
    tags:
      - Analytics
    responses:
      200:
        description: Status message
        schema:
          type: object
          properties:
            status:
              type: string
    """
    init_clickhouse_tables()
    return jsonify({"status": "ClickHouse tables initialized"})


@analytics_bp.get('/analytics/rebuild-clickhouse')
@authorize(["admin"])
def rebuild_clickhouse():
    """
    Rebuild ClickHouse table from Cassandra logs.
    ---
    tags:
      - Analytics
    responses:
      200:
        description: Status message
        schema:
          type: object
          properties:
            status:
              type: string
    """
    rebuild()
    return jsonify({"status": "ClickHouse rebuilt from Cassandra"})
