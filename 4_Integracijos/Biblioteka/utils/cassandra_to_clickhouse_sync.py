import time
from datetime import datetime, timezone
from utils.clickhouse_conn import get_clickhouse_client
from utils.cassandra_conn import get_cassandra_session

POLL_SECONDS = int(__import__('os').environ.get('CH_SYNC_POLL', 10))

def cassandra_row_to_list(row):
    # Adjust attribute access depending on your cassandra row mapping
    return [
        str(row.book_id) if row.book_id is not None else "",
        str(row.copy_id) if getattr(row, 'copy_id', None) is not None else "",
        str(row.user_id) if getattr(row, 'user_id', None) is not None else "",
        row.action_type if getattr(row, 'action_type', None) is not None else "",
        row.book_title if getattr(row, 'book_title', None) is not None else "",
        row.action_time.replace(tzinfo=timezone.utc) if getattr(row, 'action_time', None) is not None else datetime.now(timezone.utc),
        row.details if getattr(row, 'details', None) is not None else "",
    ]

def sync_loop():
    client = get_clickhouse_client()
    session = get_cassandra_session()

    # Initial last_sync: now - small buffer to avoid missing near-simultaneous events
    last_sync = datetime.now(timezone.utc)

    print("Starting Cassandra->ClickHouse sync (polling every %s seconds)..." % POLL_SECONDS)

    while True:
        try:
            # Use ALLOW FILTERING only if your table allows it. For production, design proper primary keys.
            query = """
                SELECT book_id, action_time, action_type, copy_id, user_id, book_title, details
                FROM book_actions_by_book
                WHERE action_time > %s
            """

            rows = session.execute(query, (last_sync,))

            batch = []
            for row in rows:
                batch.append(cassandra_row_to_list(row))

            if batch:
                # Insert into ClickHouse. Column order must match table definition.
                client.insert(
                    table='library_analytics.book_actions',
                    data=batch,
                    column_names=['book_id', 'copy_id', 'user_id', 'action_type', 'book_title', 'action_time', 'details']
                )
                print(f"Inserted {len(batch)} rows into ClickHouse")

            # Advance last_sync regardless of found rows
            last_sync = datetime.now(timezone.utc)

        except Exception as e:
            print("Sync error:", e)

        time.sleep(POLL_SECONDS)

if __name__ == '__main__':
    sync_loop()