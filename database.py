import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger("stillspace.database")

DB_PATH = os.getenv("DB_PATH", "search_history.db")

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_lat REAL NOT NULL,
                    start_lon REAL NOT NULL,
                    end_lat REAL NOT NULL,
                    end_lon REAL NOT NULL,
                    mode TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Database initialized at %s", DB_PATH)
    except sqlite3.Error as e:
        logger.error("Database initialization failed: %s", e)

def insert_search(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_history (start_lat, start_lon, end_lat, end_lon, mode, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (start_lat, start_lon, end_lat, end_lon, mode, datetime.utcnow().isoformat()))
            conn.commit()
    except sqlite3.Error as e:
        logger.error("Failed to insert search record: %s", e)

def get_recent_searches(limit: int = 10):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, start_lat, start_lon, end_lat, end_lon, mode, timestamp 
                FROM search_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("Failed to extract search history: %s", e)
        return []

def delete_search(search_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_history WHERE id = ?", (search_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error("Failed to delete search record: %s", e)
        return False
