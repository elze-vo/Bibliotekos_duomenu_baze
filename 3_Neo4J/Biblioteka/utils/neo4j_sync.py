# utils/neo4j_sync.py
from Biblioteka.utils.mongo_conn import get_mongo_db
from Biblioteka.utils.cassandra_conn import get_cassandra_session
from Biblioteka.utils.neo4j_recommendations import add_book_with_genres, add_read_event

db = get_mongo_db()
session = get_cassandra_session()


def sync_books():
    """Sync all books from MongoDB into Neo4j."""
    books_cursor = db.books.find()

    count = 0
    for book in books_cursor:
        isbn = book["_id"]
        title = book.get("title", "Unknown Title")
        genres = book.get("tags", [])  # uses tags array

        add_book_with_genres(isbn, title, genres)
        count += 1

    return {"status": "ok", "count": count}


def sync_user_reads(user_ids):
    """
    Sync borrowed books from Cassandra to Neo4j by user list.

    Parameters:
    - user_ids: list of user identifiers, either as integers (1,2,3) or
      full strings ('reader_1', 'reader_2')
    """
    count = 0

    for user_id in user_ids:
        # Ensure user_id has 'reader_' prefix
        if isinstance(user_id, int) or not str(user_id).startswith("reader_"):
            cass_user_id = f"reader_{user_id}"
        else:
            cass_user_id = str(user_id)

        # Query Cassandra for this user
        rows = session.execute(
            "SELECT user_id, book_id, action_type FROM book_actions_by_user WHERE user_id=%s",
            [cass_user_id]
        )

        # Add READ events to Neo4j
        for row in rows:
            if row.action_type == 'taken':
                add_read_event(row.user_id, row.book_id)
                count += 1

    return {"imports": count}

def get_all_user_ids():
    """Fetch all user IDs from MongoDB."""
    return [u["_id"] for u in db.users.find({}, {"_id": 1})]

