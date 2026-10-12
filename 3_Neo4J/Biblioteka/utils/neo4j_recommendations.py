from Biblioteka.utils.neo4j_conn import get_neo4j_session

def add_book_with_genres(book_id: str, title: str, genres: list[str]):
    """Create Book node and its Genre nodes."""
    with get_neo4j_session() as session:
        session.run("""
            MERGE (b:Book {id: $book_id})
            SET b.title = $title
            WITH b
            UNWIND $genres AS g
                MERGE (genre:Genre {name: g})
                MERGE (b)-[:HAS_GENRE]->(genre)
        """, book_id=book_id, title=title, genres=genres)


def add_read_event(user_id: str, book_id: str):
    """Create User and READ relationship."""
    with get_neo4j_session() as session:
        session.run("""
            MERGE (u:User {id: $user_id})
            MERGE (b:Book {id: $book_id})
            MERGE (u)-[:READ]->(b)
        """, user_id=user_id, book_id=book_id)

# --- Unlimited depth --- #

def recommend_books_from_similar_users_unlimited(user_id: str):
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (u:User {id: $user_id})-[:READ*1..]->(b:Book)<-[:READ*1..]-(other:User)
            WITH DISTINCT u, other
            MATCH (other)-[:READ]->(rec:Book)
            WHERE NOT EXISTS( (u)-[:READ]->(rec) )
            RETURN rec.id AS book_id, rec.title AS title, COUNT(*) AS score
            ORDER BY score DESC
        """, user_id=user_id)
        return [{"id": r["book_id"], "title": r["title"], "score": r["score"]} for r in result]

def recommend_books_from_similar_genres_unlimited(user_id: str):
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (u:User {id: $user_id})-[:READ]->(b:Book)-[:HAS_GENRE*1..]->(g:Genre)<-[:HAS_GENRE*1..]-(rec:Book)
            WHERE NOT EXISTS( (u)-[:READ]->(rec) )
            RETURN rec.id AS book_id, rec.title AS title, COUNT(*) AS score
            ORDER BY score DESC
        """, user_id=user_id)
        return [{"id": r["book_id"], "title": r["title"], "score": r["score"]} for r in result]


# --- Limited depth (shallow) --- #

def recommend_books_from_similar_users_limited(user_id: str):
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (u:User {id: $user_id})-[:READ]->(b:Book)<-[:READ]-(other:User)
            MATCH (other)-[:READ]->(rec:Book)
            WHERE NOT EXISTS( (u)-[:READ]->(rec) )
            RETURN rec.id AS book_id, rec.title AS title, COUNT(*) AS score
            ORDER BY score DESC
        """, user_id=user_id)
        return [{"id": r["book_id"], "title": r["title"], "score": r["score"]} for r in result]

def recommend_books_from_similar_genres_limited(user_id: str):
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (u:User {id: $user_id})-[:READ]->(b:Book)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(rec:Book)
            WHERE NOT EXISTS( (u)-[:READ]->(rec) )
            RETURN rec.id AS book_id, rec.title AS title, COUNT(*) AS score
            ORDER BY score DESC
        """, user_id=user_id)
        return [{"id": r["book_id"], "title": r["title"], "score": r["score"]} for r in result]

