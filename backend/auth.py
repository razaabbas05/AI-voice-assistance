"""
Authentication Module - User signup, login, JWT management
"""

import sqlite3
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

# Secret key for JWT (in production, use environment variable)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = 24  # hours

def _get_db_path():
    """Get database path"""
    return os.path.join(os.path.dirname(__file__), "sessions.db")

def init_auth_db():
    """Create users table if not exists"""
    db_path = _get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Add user_id to sessions table if not exists
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER REFERENCES users(id)")
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()

def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_user(email: str, username: str, password: str) -> Optional[Dict]:
    """Create a new user, returns user dict or None if failed"""
    db_path = _get_db_path()
    password_hash = hash_password(password)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (email, username, password_hash)
            )
            conn.commit()
            
            return {
                "id": cursor.lastrowid,
                "email": email,
                "username": username
            }
    except sqlite3.IntegrityError:
        return None  # Email or username already exists

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate user by email and password"""
    db_path = _get_db_path()
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user and verify_password(password, user["password_hash"]):
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"]
            }
    
    return None

def create_token(user_id: int) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[int]:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    db_path = _get_db_path()
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT id, email, username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"]
            }
    return None