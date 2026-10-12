from Biblioteka.utils.clickhouse_conn import get_clickhouse_client

def init_clickhouse_tables():
    client = get_clickhouse_client()

    client.command("CREATE DATABASE IF NOT EXISTS library_analytics")

    client.command("USE library_analytics")

    client.command("""
    CREATE TABLE IF NOT EXISTS library_analytics.book_actions (
        book_id String,
        copy_id String,
        user_id String,
        action_type String,
        book_title String,
        action_time DateTime,
        details String
    )
    ENGINE = MergeTree()
    ORDER BY action_time
    """)

if __name__ == "__main__":
    init_clickhouse_tables()
    print("ClickHouse tables initialized.")