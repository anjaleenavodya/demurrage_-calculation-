import sqlite3
import os
import hashlib
import json
import datetime
from typing import List, Optional, Tuple, Dict

DB_NAME = "demurrage.db"

def load_env():
    # .env is in the same directory as this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

# Run immediately to load env vars
load_env()

def get_db_path() -> str:
    # Always keep the DB in the Intern folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)

def get_connection(db_path: str = None) -> sqlite3.Connection:
    if not db_path:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Secure password hashing without external libraries
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{pwd_hash.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, hash_hex = hashed_password.split(':')
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return pwd_hash.hex() == hash_hex
    except Exception:
        return False

def init_db(db_path: str = None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)
    
    # 2. Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
    )
    """)
    
    # 3. Calculations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_name TEXT NOT NULL,
        cargo_type TEXT NOT NULL,
        berth_type TEXT NOT NULL,
        laycan_start TEXT NOT NULL,
        laycan_end TEXT NOT NULL,
        arrival_time TEXT NOT NULL,
        nor_tendered TEXT NOT NULL,
        nor_accepted TEXT NOT NULL,
        loading_arm_disconnected TEXT NOT NULL,
        terminal_requested_early INTEGER NOT NULL,
        terminal_granted_permission_late INTEGER NOT NULL,
        berths_count INTEGER NOT NULL,
        vessel_delays_json TEXT NOT NULL,
        terminal_delays_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(username) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    
    # Seed default admin user if none exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_username = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
        admin_password = os.environ.get("ADMIN_PASSWORD", "adminpassword")
        admin_hash = hash_password(admin_password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (admin_username, admin_hash, "admin")
        )
        conn.commit()
        
    conn.close()

# User Operations
def create_user(username: str, plain_password: str, role: str = "user", db_path: str = None) -> bool:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        pwd_hash = hash_password(plain_password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip().lower(), pwd_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_user(username: str, db_path: str = None) -> bool:
    # Cannot delete the main admin account
    protected_admin = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
    if username.strip().lower() == protected_admin:
        return False
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username.strip().lower(),))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def list_users(db_path: str = None) -> List[Dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users ORDER BY username ASC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

# Session Operations
def create_session(username: str, db_path: str = None) -> str:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    token = os.urandom(24).hex()
    
    # Session valid for 24 hours
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
    cursor.execute(
        "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
        (token, username.strip().lower(), expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    return token

def validate_session(token: str, db_path: str = None) -> Optional[Dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.username, u.role, s.expires_at 
        FROM sessions s 
        JOIN users u ON s.username = u.username 
        WHERE s.token = ?
    """, (token,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    expires_at = datetime.datetime.fromisoformat(row['expires_at'])
    if datetime.datetime.now() > expires_at:
        # Session expired, delete it
        delete_session(token, db_path)
        return None
        
    return {"username": row['username'], "role": row['role']}

def delete_session(token: str, db_path: str = None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

# Calculation Operations
def save_calculation(username: str, req_data: Dict, res_data: Dict, db_path: str = None) -> int:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO calculations (
            vessel_name, cargo_type, berth_type, laycan_start, laycan_end,
            arrival_time, nor_tendered, nor_accepted, loading_arm_disconnected,
            terminal_requested_early, terminal_granted_permission_late, berths_count,
            vessel_delays_json, terminal_delays_json, result_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req_data['vessel_name'],
        req_data['cargo_type'],
        req_data['berth_type'],
        req_data['laycan_start'],
        req_data['laycan_end'],
        req_data['arrival_time'],
        req_data['nor_tendered'],
        req_data['nor_accepted'],
        req_data['loading_arm_disconnected'],
        1 if req_data.get('terminal_requested_early', False) else 0,
        1 if req_data.get('terminal_granted_permission_late', False) else 0,
        req_data.get('berths_count', 1),
        json.dumps(req_data.get('vessel_delays', [])),
        json.dumps(req_data.get('terminal_delays', [])),
        json.dumps(res_data),
        username
    ))
    conn.commit()
    calc_id = cursor.lastrowid
    conn.close()
    return calc_id

def get_calculations(username: str, role: str, db_path: str = None) -> List[Dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Admins can view all history; regular users can only view their own
    if role == "admin":
        cursor.execute("SELECT * FROM calculations ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT * FROM calculations WHERE created_by = ? ORDER BY created_at DESC", (username,))
        
    rows = cursor.fetchall()
    conn.close()
    
    calcs = []
    for row in rows:
        calc = dict(row)
        calc['vessel_delays'] = json.loads(calc['vessel_delays_json'])
        calc['terminal_delays'] = json.loads(calc['terminal_delays_json'])
        calc['result'] = json.loads(calc['result_json'])
        calcs.append(calc)
    return calcs

def delete_calculation(calc_id: int, username: str, role: str, db_path: str = None) -> bool:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Non-admins can only delete their own calculations
    if role == "admin":
        cursor.execute("DELETE FROM calculations WHERE id = ?", (calc_id,))
    else:
        cursor.execute("DELETE FROM calculations WHERE id = ? AND created_by = ?", (calc_id, username))
        
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0
