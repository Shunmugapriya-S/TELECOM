import os
import sqlite3
import hashlib
import time
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("telecom_db")
logger.setLevel(logging.INFO)

# Check PostgreSQL environment configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "telecom_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Fallback SQLite DB path if PostgreSQL driver or service is unavailable
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "telecom_app.db")

USE_POSTGRES = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Test PostgreSQL connection with short timeout
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=2
    )
    conn.close()
    USE_POSTGRES = True
    logger.info(f"Connected to PostgreSQL database '{POSTGRES_DB}' at {POSTGRES_HOST}:{POSTGRES_PORT}")
except Exception as err:
    logger.warning(f"PostgreSQL connection unavailable ({err}). Using SQLite fallback at '{SQLITE_DB_PATH}'.")
    USE_POSTGRES = False

def get_connection():
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id VARCHAR(64) PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(32) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                account_type VARCHAR(32) DEFAULT 'Prepaid',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                customer_id VARCHAR(64) REFERENCES customers(id),
                token VARCHAR(255) NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_queries (
                query_id VARCHAR(64) PRIMARY KEY,
                customer_id VARCHAR(64) REFERENCES customers(id),
                session_id VARCHAR(64),
                input_type VARCHAR(16) NOT NULL,
                raw_query TEXT,
                transcript TEXT,
                english_translation TEXT,
                category VARCHAR(64),
                sub_category VARCHAR(64),
                sentiment VARCHAR(32),
                priority VARCHAR(32),
                ai_response TEXT,
                orchestration_steps TEXT,
                status VARCHAR(32) DEFAULT 'resolved',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_feedbacks (
                feedback_id VARCHAR(64) PRIMARY KEY,
                customer_id VARCHAR(64) REFERENCES customers(id),
                rating INT NOT NULL,
                comments TEXT,
                thank_you_sent BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone_number TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                account_type TEXT DEFAULT 'Prepaid',
                created_at TEXT,
                last_login TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_sessions (
                session_id TEXT PRIMARY KEY,
                customer_id TEXT,
                token TEXT NOT NULL,
                login_time TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_queries (
                query_id TEXT PRIMARY KEY,
                customer_id TEXT,
                input_type TEXT NOT NULL,
                raw_query TEXT,
                transcript TEXT,
                english_translation TEXT,
                category TEXT,
                sub_category TEXT,
                sentiment TEXT,
                priority TEXT,
                ai_response TEXT,
                orchestration_steps TEXT,
                status TEXT DEFAULT 'resolved',
                created_at TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_feedbacks (
                feedback_id TEXT PRIMARY KEY,
                customer_id TEXT,
                rating INTEGER NOT NULL,
                comments TEXT,
                thank_you_sent INTEGER DEFAULT 1,
                created_at TEXT
            );
        """)

    conn.commit()
    conn.close()
    return f"DB Initialized successfully (Engine: {'PostgreSQL' if USE_POSTGRES else 'SQLite'})"

def register_customer(full_name: str, phone_number: str, email: str, password: str, account_type: str = "Prepaid") -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    clean_phone = phone_number.strip()
    if not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone if clean_phone.isdigit() else clean_phone

    cust_id = f"CUST-{int(time.time()*1000)}"
    pw_hash = hash_password(password)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        session_id = f"SESS-{int(time.time()*1000)}"
        token = f"JWT-SIM-{cust_id}-{session_id}"

        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO customers (id, full_name, phone_number, email, password_hash, account_type, created_at, last_login)
                   VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (cust_id, full_name, clean_phone, email.lower(), pw_hash, account_type)
            )
            cursor.execute(
                "INSERT INTO customer_sessions (session_id, customer_id, token, login_time) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                (session_id, cust_id, token)
            )
        else:
            cursor.execute(
                """INSERT INTO customers (id, full_name, phone_number, email, password_hash, account_type, created_at, last_login)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cust_id, full_name, clean_phone, email.lower(), pw_hash, account_type, now_str, now_str)
            )
            cursor.execute(
                "INSERT INTO customer_sessions (session_id, customer_id, token, login_time) VALUES (?, ?, ?, ?)",
                (session_id, cust_id, token, now_str)
            )
        conn.commit()
    except Exception as e:
        conn.close()
        if "unique" in str(e).lower() or "already exists" in str(e).lower():
            raise ValueError("A customer with this phone number or email already exists.")
        raise e

    conn.close()
    return {
        "id": cust_id,
        "full_name": full_name,
        "phone_number": clean_phone,
        "email": email.lower(),
        "account_type": account_type,
        "session_id": session_id,
        "token": token
    }

def login_customer(email_or_phone: str, password: str) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    raw = email_or_phone.strip()
    target_email = raw.lower()
    target_phone = raw.replace(" ", "").replace("-", "")
    phone_with_plus = "+" + target_phone if not target_phone.startswith("+") else target_phone
    phone_without_plus = target_phone.lstrip("+")

    if USE_POSTGRES:
        cursor.execute(
            """SELECT id, full_name, phone_number, email, password_hash, account_type 
               FROM customers 
               WHERE LOWER(email) = %s 
                  OR phone_number = %s 
                  OR phone_number = %s 
                  OR phone_number = %s""",
            (target_email, raw, phone_with_plus, phone_without_plus)
        )
        row = cursor.fetchone()
    else:
        cursor.execute(
            """SELECT id, full_name, phone_number, email, password_hash, account_type 
               FROM customers 
               WHERE LOWER(email) = ? 
                  OR phone_number = ? 
                  OR phone_number = ? 
                  OR phone_number = ?""",
            (target_email, raw, phone_with_plus, phone_without_plus)
        )
        row = cursor.fetchone()

    if not row:
        conn.close()
        raise ValueError("Invalid credentials. Account not found.")

    if USE_POSTGRES:
        cust_id, full_name, phone_number, email, stored_hash, account_type = row
    else:
        cust_id, full_name, phone_number, email, stored_hash, account_type = row[0], row[1], row[2], row[3], row[4], row[5]

    if stored_hash != pw_hash:
        conn.close()
        raise ValueError("Invalid password.")

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    session_id = f"SESS-{int(time.time()*1000)}"
    token = f"JWT-SIM-{cust_id}-{session_id}"

    if USE_POSTGRES:
        cursor.execute("UPDATE customers SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (cust_id,))
        cursor.execute(
            "INSERT INTO customer_sessions (session_id, customer_id, token, login_time) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
            (session_id, cust_id, token)
        )
    else:
        cursor.execute("UPDATE customers SET last_login = ? WHERE id = ?", (now_str, cust_id))
        cursor.execute(
            "INSERT INTO customer_sessions (session_id, customer_id, token, login_time) VALUES (?, ?, ?, ?)",
            (session_id, cust_id, token, now_str)
        )
    conn.commit()
    conn.close()

    return {
        "id": cust_id,
        "full_name": full_name,
        "phone_number": phone_number,
        "email": email,
        "account_type": account_type,
        "session_id": session_id,
        "token": token
    }

def get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("SELECT id, full_name, phone_number, email, account_type FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
    else:
        cursor.execute("SELECT id, full_name, phone_number, email, account_type FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "full_name": row[1],
        "phone_number": row[2],
        "email": row[3],
        "account_type": row[4]
    }

def get_customer_by_phone(phone_or_user_id: str) -> Optional[Dict[str, Any]]:
    """Checks if a user is an active registered customer in the database by phone number / WhatsApp ID."""
    if not phone_or_user_id:
        return None
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    raw = phone_or_user_id.strip()
    clean = raw.replace("@c.us", "").replace("@s.whatsapp.net", "").replace("+", "").replace(" ", "").replace("-", "")
    phone_with_plus = f"+{clean}"
    phone_without_plus = clean

    # Also handle 10-digit national format (e.g., stripping 91 country code if present)
    ten_digit = clean[-10:] if len(clean) >= 10 else clean

    if USE_POSTGRES:
        cursor.execute(
            """SELECT id, full_name, phone_number, email, account_type 
               FROM customers 
               WHERE phone_number = %s 
                  OR phone_number = %s 
                  OR phone_number LIKE %s 
                  OR id = %s""",
            (phone_with_plus, phone_without_plus, f"%{ten_digit}", raw)
        )
        row = cursor.fetchone()
    else:
        cursor.execute(
            """SELECT id, full_name, phone_number, email, account_type 
               FROM customers 
               WHERE phone_number = ? 
                  OR phone_number = ? 
                  OR phone_number LIKE ? 
                  OR id = ?""",
            (phone_with_plus, phone_without_plus, f"%{ten_digit}", raw)
        )
        row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "full_name": row[1],
        "phone_number": row[2],
        "email": row[3],
        "account_type": row[4]
    }

def save_customer_query(
    customer_id: str,
    input_type: str,
    raw_query: str,
    transcript: str,
    english_translation: str,
    category: str,
    sub_category: str,
    sentiment: str,
    priority: str,
    ai_response: str,
    orchestration_steps: List[Any],
    status: str = "resolved",
    session_id: str = ""
) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query_id = f"QRY-{int(time.time()*1000)}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    steps_json = json.dumps(orchestration_steps if orchestration_steps else [])

    if USE_POSTGRES:
        cursor.execute(
            """INSERT INTO customer_queries (
                query_id, customer_id, session_id, input_type, raw_query, transcript, english_translation,
                category, sub_category, sentiment, priority, ai_response, orchestration_steps, status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)""",
            (query_id, customer_id, session_id, input_type, raw_query, transcript, english_translation,
             category, sub_category, sentiment, priority, ai_response, steps_json, status)
        )
    else:
        cursor.execute(
            """INSERT INTO customer_queries (
                query_id, customer_id, session_id, input_type, raw_query, transcript, english_translation,
                category, sub_category, sentiment, priority, ai_response, orchestration_steps, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (query_id, customer_id, session_id, input_type, raw_query, transcript, english_translation,
             category, sub_category, sentiment, priority, ai_response, steps_json, status, now_str)
        )

    conn.commit()
    conn.close()

    return {
        "query_id": query_id,
        "customer_id": customer_id,
        "session_id": session_id,
        "input_type": input_type,
        "status": status,
        "created_at": now_str
    }

def get_latest_session(customer_id: str) -> Optional[str]:
    """Returns the most recent session_id for the given customer, or empty string if none."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute(
            "SELECT session_id FROM customer_sessions WHERE customer_id = %s ORDER BY login_time DESC LIMIT 1",
            (customer_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    else:
        cursor.execute(
            "SELECT session_id FROM customer_sessions WHERE customer_id = ? ORDER BY login_time DESC LIMIT 1",
            (customer_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row["session_id"] if row else ""

def save_service_feedback(customer_id: str, rating: int, comments: str) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    feedback_id = f"FBK-{int(time.time()*1000)}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    if USE_POSTGRES:
        cursor.execute(
            """INSERT INTO service_feedbacks (feedback_id, customer_id, rating, comments, thank_you_sent, created_at)
               VALUES (%s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)""",
            (feedback_id, customer_id, rating, comments)
        )
    else:
        cursor.execute(
            """INSERT INTO service_feedbacks (feedback_id, customer_id, rating, comments, thank_you_sent, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (feedback_id, customer_id, rating, comments, now_str)
        )

    conn.commit()
    conn.close()

    return {
        "feedback_id": feedback_id,
        "customer_id": customer_id,
        "rating": rating,
        "comments": comments,
        "thank_you_sent": True,
        "created_at": now_str
    }

def get_customer_queries(customer_id: str) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute(
            """SELECT query_id, customer_id, input_type, raw_query, transcript, english_translation,
                      category, sub_category, sentiment, priority, ai_response, status, created_at
               FROM customer_queries WHERE customer_id = %s ORDER BY created_at DESC LIMIT 20""",
            (customer_id,)
        )
        rows = cursor.fetchall()
        queries = []
        for r in rows:
            queries.append({
                "query_id": r[0], "customer_id": r[1], "input_type": r[2], "raw_query": r[3],
                "transcript": r[4], "english_translation": r[5], "category": r[6],
                "sub_category": r[7], "sentiment": r[8], "priority": r[9],
                "ai_response": r[10], "status": r[11], "created_at": str(r[12])
            })
    else:
        cursor.execute(
            """SELECT query_id, customer_id, input_type, raw_query, transcript, english_translation,
                      category, sub_category, sentiment, priority, ai_response, status, created_at
               FROM customer_queries WHERE customer_id = ? ORDER BY created_at DESC LIMIT 20""",
            (customer_id,)
        )
        rows = cursor.fetchall()
        queries = []
        for r in rows:
            queries.append({
                "query_id": r["query_id"], "customer_id": r["customer_id"], "input_type": r["input_type"],
                "raw_query": r["raw_query"], "transcript": r["transcript"], "english_translation": r["english_translation"],
                "category": r["category"], "sub_category": r["sub_category"], "sentiment": r["sentiment"],
                "priority": r["priority"], "ai_response": r["ai_response"], "status": r["status"],
                "created_at": r["created_at"]
            })

    conn.close()
    return queries

def get_query_frequency(customer_id: str, category: str = "") -> int:
    """Calculates occurrence count of customer queries by category to drive frequency-based escalation."""
    queries = get_customer_queries(customer_id)
    if not category:
        return len(queries) + 1
    count = sum(1 for q in queries if q.get("category", "").strip().lower() == category.strip().lower())
    return count + 1

# Initialize database tables on load
init_db()
