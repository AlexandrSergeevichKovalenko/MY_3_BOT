import psycopg2
import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL_RAILWAY")

@contextmanager
def get_db_connection_context():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    text TEXT NOT NULL,
                    errors TEXT,
                    topic_id INT REFERENCES topics(id),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Вставка тем
            topics = [
                "Essen und Restaurants", "Reisen und Urlaub", "Arbeit und Beruf",
                "Hobbys und Freizeit", "Familie und Freunde"
            ]
            for topic in topics:
                cursor.execute("""
                    INSERT INTO topics (name) VALUES (%s)
                    ON CONFLICT (name) DO NOTHING;
                """, (topic,))

async def save_error(user_id: int, text: str, errors: str, topic_id: int):
    with get_db_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO errors (user_id, text, errors, topic_id)
                VALUES (%s, %s, %s, %s);
            """, (user_id, text, errors, topic_id))

async def suggest_topic(user_id: int) -> str:
    with get_db_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT t.name
                FROM topics t
                LEFT JOIN (
                    SELECT topic_id, COUNT(*) as error_count
                    FROM errors
                    WHERE user_id = %s
                    GROUP BY topic_id
                    ORDER BY error_count DESC
                    LIMIT 1
                ) e ON t.id = e.topic_id
                ORDER BY e.error_count DESC NULLS LAST
                LIMIT 1;
            """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else "Essen und Restaurants"

async def get_topic_by_id(topic_id: int) -> dict:
    with get_db_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM topics WHERE id = %s;", (topic_id,))
            result = cursor.fetchone()
            return {"id": result[0], "name": result[1]} if result else None

async def get_all_topics() -> list:
    with get_db_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM topics;")
            return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]