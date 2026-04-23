"""
Session Manager - SQLite storage for chat sessions and messages
"""

import aiosqlite
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = "sessions.db"

async def init_db():
    """Create tables if they don't exist"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                user_id INTEGER,
                created_at TIMESTAMP,
                last_updated TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                emotion TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        # Add user_id column if it doesn't exist (for existing databases)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
        except:
            pass
        await db.commit()
    print("✅ Database initialized")

async def create_session(session_id: str, user_id: int = None, title: str = "New Chat"):
    """Create a new session record"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title, user_id, created_at, last_updated) VALUES (?, ?, ?, ?, ?)",
            (session_id, title, user_id, now, now)
        )
        await db.commit()

async def update_session_timestamp(session_id: str, user_id: int = None):
    """Update last_updated and optionally set user_id"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            await db.execute(
                "UPDATE sessions SET last_updated = ?, user_id = ? WHERE session_id = ?",
                (now, user_id, session_id)
            )
        else:
            await db.execute(
                "UPDATE sessions SET last_updated = ? WHERE session_id = ?",
                (now, session_id)
            )
        await db.commit()

async def update_session_title(session_id: str, title: str):
    """Manually update session title"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET title = ? WHERE session_id = ?",
            (title, session_id)
        )
        await db.commit()

async def list_sessions(user_id: int = None) -> List[Dict]:
    """Get all sessions, optionally filtered by user"""
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            cursor = await db.execute(
                "SELECT session_id, title, created_at, last_updated FROM sessions WHERE user_id = ? ORDER BY last_updated DESC",
                (user_id,)
            )
        else:
            cursor = await db.execute(
                "SELECT session_id, title, created_at, last_updated FROM sessions ORDER BY last_updated DESC"
            )
        rows = await cursor.fetchall()
        return [
            {
                "session_id": row[0],
                "title": row[1],
                "created_at": row[2],
                "last_updated": row[3]
            }
            for row in rows
        ]

async def delete_session(session_id: str):
    """Delete a session and all its messages"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.commit()

async def save_message(session_id: str, role: str, content: str, emotion: str = "neutral"):
    """Save a single message"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, emotion, timestamp) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, emotion, now)
        )
        await db.execute(
            "UPDATE sessions SET last_updated = ? WHERE session_id = ?",
            (now, session_id)
        )
        await db.commit()

async def get_session_messages(session_id: str) -> List[Dict]:
    """Retrieve all messages for a session"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT role, content, emotion, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        )
        rows = await cursor.fetchall()
        return [
            {"role": row[0], "content": row[1], "emotion": row[2], "timestamp": row[3]}
            for row in rows
        ]

async def auto_generate_title(session_id: str, first_message: str):
    """Set title from first few words of first user message"""
    title = first_message[:30] + ("..." if len(first_message) > 30 else "")
    await update_session_title(session_id, title)

# These are kept for backward compatibility
async def create_session_for_user(session_id: str, user_id: int, title: str = "New Chat"):
    return await create_session(session_id, user_id, title)

async def list_sessions_for_user(user_id: int) -> List[Dict]:
    return await list_sessions(user_id)