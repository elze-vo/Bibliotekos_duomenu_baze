from Biblioteka.utils.clickhouse_conn import get_clickhouse_client
from Biblioteka.utils.cassandra_conn import get_cassandra_session

def rebuild():
    client = get_clickhouse_client()
    session = get_cassandra_session()

    print("Truncating ClickHouse table library_analytics.book_actions...")
    client.command("TRUNCATE TABLE library_analytics.book_actions")

    print("Reading all rows from Cassandra book_actions_by_book (this may take a while)...")
    rows = session.execute("SELECT book_id, action_time, action_type, copy_id, user_id, book_title, details FROM book_actions_by_book")

    batch = []
    count = 0
    for row in rows:
        batch.append([
            str(row.book_id) if row.book_id is not None else "",
            str(getattr(row, 'copy_id', '')),
            str(getattr(row, 'user_id', '')),
            getattr(row, 'action_type', ''),
            getattr(row, 'book_title', ''),
            getattr(row, 'action_time', None),
            getattr(row, 'details', '') or ''
        ])
        count += 1

        # Insert in batches to avoid huge memory usage
        if len(batch) >= 1000:
            client.insert('library_analytics.book_actions', batch)
            batch = []

    if batch:
        client.insert('library_analytics.book_actions', batch)

    print(f"Rebuild finished. Inserted {count} rows.")

if __name__ == '__main__':
    rebuild()