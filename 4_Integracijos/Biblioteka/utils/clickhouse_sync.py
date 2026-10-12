from datetime import datetime, timezone
from Biblioteka.utils.clickhouse_conn import get_clickhouse_client

def sync_book_action_to_clickhouse(
    user_id: str,
    book_id: str,
    copy_id: str,
    action_type: str,
    book_title: str,
    details: str = "",
    action_time: datetime = None
):
    """
    Synchronize book action to ClickHouse immediately after logging to Cassandra.
    
    Args:
        user_id: User ID (e.g., "reader_42")
        book_id: Book ID
        copy_id: Copy ID
        action_type: Action type (e.g., "taken", "returned", "reserved", "reservation_cancelled")
        book_title: Title of the book
        details: Additional details about the action
        action_time: Timestamp of the action (defaults to now)
    """
    try:
        client = get_clickhouse_client()
        
        if action_time is None:
            action_time = datetime.now(timezone.utc)

        if action_time.tzinfo is None:
            action_time = action_time.replace(tzinfo=timezone.utc)

        data = [[
            str(book_id),
            str(copy_id),
            str(user_id),
            str(action_type),
            str(book_title),
            action_time,
            str(details)
        ]]
        
        client.insert(
            table='library_analytics.book_actions',
            data=data,
            column_names=['book_id', 'copy_id', 'user_id', 'action_type', 'book_title', 'action_time', 'details']
        )
        
        print(f"Synced to ClickHouse: {action_type} for book {book_id} by {user_id}")
        
    except Exception as e:
        print(f"ClickHouse sync error: {e}")
