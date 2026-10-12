from datetime import datetime, date
from Biblioteka.utils.cassandra_conn import get_cassandra_session

session = get_cassandra_session()

def log_system_event(user_id, event_type, entity_type, entity_id, details=""):
    print(f"[LOG] {user_id} {event_type} {entity_type} {entity_id}")
    event_time = datetime.utcnow()
    event_date = date.today()

    session.execute("""
        INSERT INTO system_events_by_user (user_id, event_time, event_type, entity_type, entity_id, details)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, event_time, event_type, entity_type, entity_id, details))

    session.execute("""
        INSERT INTO system_events_by_date (event_date, event_time, user_id, event_type, entity_type, entity_id, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (event_date, event_time, user_id, event_type, entity_type, entity_id, details))

def log_book_action(user_id, book_id, copy_id, action_type, book_title, details=""):
    print(f"[BOOK ACTION] {user_id} {action_type} book:{book_id} copy:{copy_id}")
    event_time = datetime.utcnow()

    session.execute("""
        INSERT INTO book_actions_by_user (user_id, action_time, action_type, book_id, copy_id, book_title, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, event_time, action_type, book_id, copy_id, book_title, details))

    session.execute("""
        INSERT INTO book_actions_by_book (book_id, action_time, action_type, copy_id, user_id, book_title, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (book_id, event_time, action_type, copy_id, user_id, book_title, details))
