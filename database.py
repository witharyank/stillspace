import sqlite3
import os
import logging
from datetime import datetime, timezone

# Create logger for database-related logs
logger = logging.getLogger("stillspace.database")

# Database file path (can be overridden using environment variable)
DB_PATH = os.getenv("DB_PATH", "search_history.db")


# Function to initialize the database and create table if it doesn't exist
def init_db():
    try:
        # Connect to SQLite database
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            cursor = conn.cursor()

            # Create search_history table
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

            # Save changes
            conn.commit()

            # Log success message
            logger.info("Database initialized at %s", DB_PATH)

    except sqlite3.Error as e:
        # Log error if database creation fails
        logger.error("Database initialization failed: %s", e)


# Function to insert a new search record into database
def insert_search(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str):
    try:
        # Open database connection
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            cursor = conn.cursor()

            # Insert search data into table
            cursor.execute("""
                INSERT INTO search_history (start_lat, start_lon, end_lat, end_lon, mode, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                start_lat,
                start_lon,
                end_lat,
                end_lon,
                mode,
                datetime.now(timezone.utc).isoformat()  # Current UTC time
            ))

            # Save changes
            conn.commit()

    except sqlite3.Error as e:
        # Log error if insertion fails
        logger.error("Failed to insert search record: %s", e)


# Function to get recent searches from database
def get_recent_searches(limit: int = 10):
    try:
        # Open database connection
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:

            # Return rows as dictionary-like objects
            conn.row_factory = sqlite3.Row

            cursor = conn.cursor()

            # Fetch recent searches ordered by latest timestamp
            cursor.execute("""
                SELECT id, start_lat, start_lon, end_lat, end_lon, mode, timestamp 
                FROM search_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))

            # Get all rows
            rows = cursor.fetchall()

            # Convert rows into list of dictionaries
            return [dict(row) for row in rows]

    except sqlite3.Error as e:
        # Log error if fetching fails
        logger.error("Failed to extract search history: %s", e)

        # Return empty list on failure
        return []


# Function to delete a search record using its ID
def delete_search(search_id: int):
    try:
        # Open database connection
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            cursor = conn.cursor()

            # Delete record matching given ID
            cursor.execute(
                "DELETE FROM search_history WHERE id = ?",
                (search_id,)
            )

            # Save changes
            conn.commit()

            # Return True if record was deleted successfully
            return cursor.rowcount > 0

    except sqlite3.Error as e:
        # Log error if deletion fails
        logger.error("Failed to delete search record: %s", e)
        # Return False on failure
        return False