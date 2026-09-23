import sqlite3
import os
import hashlib
import uuid
from typing import Optional
from fastapi import HTTPException, Request

try:
    import psycopg2
    import psycopg2.extras as psycopg2_extras
except ImportError:
    psycopg2 = None
    psycopg2_extras = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

import shutil
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")
LEGACY_DB_PATH = os.path.join(DB_DIR, "shadowcall_ai.db")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "mikey.db")

# If legacy database exists but mikey.db does not, safely copy it over to prevent data loss
if os.path.exists(LEGACY_DB_PATH) and not os.path.exists(DEFAULT_DB_PATH):
    try:
        shutil.copy2(LEGACY_DB_PATH, DEFAULT_DB_PATH)
    except Exception:
        pass

DB_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH if os.path.exists(DEFAULT_DB_PATH) else LEGACY_DB_PATH)

# Ensure the DB directory exists
os.makedirs(DB_DIR, exist_ok=True)

# ── Database helpers ────────────────────────────────────────────────────────

def get_db_connection():
    if DATABASE_URL:
        if psycopg2 is None or psycopg2_extras is None:
            raise RuntimeError("psycopg2 is not installed. Install it or remove DATABASE_URL.")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2_extras.RealDictCursor)
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_execute(conn, query: str, params: tuple = ()): 
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur
    return conn.execute(query, params)


def sql_query(query: str) -> str:
    return query.replace('?', '%s') if DATABASE_URL else query


def init_db():
    conn = get_db_connection()
    if DATABASE_URL:
        conn.cursor().execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                is_approved BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                lang TEXT DEFAULT 'en',
                tts_enabled BOOLEAN DEFAULT TRUE,
                voice_input_enabled BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            
            CREATE TABLE IF NOT EXISTS chat_threads (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                pinned BOOLEAN DEFAULT FALSE,
                archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                endpoint TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    else:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'en',
                tts_enabled INTEGER DEFAULT 1,
                voice_input_enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            
            CREATE TABLE IF NOT EXISTS chat_threads (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                pinned INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                endpoint TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                success INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()

    # Migration check for is_admin & is_approved columns in case table existed previously
    if DATABASE_URL:
        try: db_execute(conn, "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"); conn.commit()
        except Exception: pass
        try: db_execute(conn, "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE"); conn.commit()
        except Exception: pass
    else:
        try: db_execute(conn, "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"); conn.commit()
        except Exception: pass
        try: db_execute(conn, "ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1"); conn.commit()
        except Exception: pass

    # Seed Admin Users ('Ganesh', 'gani', 'gann') with password 'gani**38'
    for admin_name in ["Ganesh", "gani", "gann"]:
        try:
            sql = sql_query("SELECT id FROM users WHERE username = ?")
            existing_admin = db_execute(conn, sql, (admin_name,)).fetchone()
            admin_pass_hash = hash_password("gani**38")
            if not existing_admin:
                ins_sql = sql_query("INSERT INTO users (username, password_hash, is_admin, is_approved) VALUES (?, ?, ?, ?)")
                db_execute(conn, ins_sql, (admin_name, admin_pass_hash, 1, 1))
                conn.commit()
            else:
                upd_sql = sql_query("UPDATE users SET is_admin = 1, is_approved = 1 WHERE username = ?")
                db_execute(conn, upd_sql, (admin_name,))
                conn.commit()
        except Exception as e:
            print(f"Error seeding admin user {admin_name}: {e}")

    # Set non-admin accounts like 'hii' to is_approved = 0 so admin must explicitly approve them
    try:
        db_execute(conn, "UPDATE users SET is_approved = 0 WHERE is_admin = 0 AND username = 'hii'")
        conn.commit()
    except Exception:
        pass

    conn.close()


def hash_password(password: str, salt: bytes = b"mikey-salt") -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()


def verify_password(stored_hash: str, password: str) -> bool:
    if not stored_hash or not password:
        return False
    # Check new salt first
    if stored_hash == hash_password(password, b"mikey-salt"):
        return True
    # Check legacy shadowcall salt for backwards compatibility
    if stored_hash == hash_password(password, b"shadowcall-salt"):
        return True
    return False


def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    sql = sql_query("INSERT INTO sessions (id, user_id) VALUES (?, ?)")
    db_execute(conn, sql, (session_id, user_id))
    conn.commit()
    conn.close()
    return session_id


def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    conn = get_db_connection()
    sql = sql_query("SELECT u.id, u.username, u.is_admin FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?")
    row = db_execute(conn, sql, (session_id,)).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}
    return None


def get_preferences(user_id: int):
    conn = get_db_connection()
    sql = sql_query("SELECT lang, tts_enabled, voice_input_enabled FROM user_preferences WHERE user_id = ?")
    row = db_execute(conn, sql, (user_id,)).fetchone()
    conn.close()
    if row:
        return {
            "lang": row["lang"] or "en",
            "tts_enabled": bool(row["tts_enabled"]),
            "voice_input_enabled": bool(row["voice_input_enabled"]),
        }
    return {"lang": "en", "tts_enabled": True, "voice_input_enabled": True}


def save_preferences(user_id: int, lang: Optional[str] = None, tts_enabled: Optional[bool] = None, voice_input_enabled: Optional[bool] = None):
    conn = get_db_connection()
    sql = sql_query("SELECT 1 FROM user_preferences WHERE user_id = ?")
    existing = db_execute(conn, sql, (user_id,)).fetchone()
    if existing:
        sql = sql_query("UPDATE user_preferences SET lang = COALESCE(?, lang), tts_enabled = COALESCE(?, tts_enabled), voice_input_enabled = COALESCE(?, voice_input_enabled), updated_at = CURRENT_TIMESTAMP WHERE user_id = ?")
        db_execute(conn, sql, (lang, 1 if tts_enabled is True else 0 if tts_enabled is False else None, 1 if voice_input_enabled is True else 0 if voice_input_enabled is False else None, user_id))
    else:
        sql = sql_query("INSERT INTO user_preferences (user_id, lang, tts_enabled, voice_input_enabled) VALUES (?, ?, ?, ?)")
        db_execute(conn, sql, (user_id, lang or "en", 1 if tts_enabled is not False else 0, 1 if voice_input_enabled is not False else 0))
    conn.commit()
    conn.close()


def save_conversation(user_id: int, role: str, content: str):
    conn = get_db_connection()
    sql = sql_query("INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)")
    db_execute(conn, sql, (user_id, role, content))
    conn.commit()
    conn.close()


def log_event(user_id: Optional[int], event_type: str, metadata: Optional[str] = None):
    conn = get_db_connection()
    sql = sql_query("INSERT INTO analytics (user_id, event_type, metadata) VALUES (?, ?, ?)")
    db_execute(conn, sql, (user_id, event_type, metadata))
    conn.commit()
    conn.close()


def log_api_usage(user_id: Optional[int], endpoint: str, response_time_ms: int, success: bool):
    conn = get_db_connection()
    sql = sql_query("INSERT INTO api_usage (user_id, endpoint, response_time_ms, success) VALUES (?, ?, ?, ?)")
    db_execute(conn, sql, (user_id, endpoint, response_time_ms, 1 if success else 0))
    conn.commit()
    conn.close()


def add_reminder(user_id: int, title: str, scheduled_at: str, description: Optional[str] = None):
    conn = get_db_connection()
    sql = sql_query("INSERT INTO reminders (user_id, title, scheduled_at, description) VALUES (?, ?, ?, ?)")
    db_execute(conn, sql, (user_id, title, scheduled_at, description))
    conn.commit()
    conn.close()


def complete_reminder(user_id: int, reminder_id: int):
    conn = get_db_connection()
    sql = sql_query("UPDATE reminders SET completed = ? WHERE id = ? AND user_id = ?")
    db_execute(conn, sql, (1, reminder_id, user_id))
    conn.commit()
    conn.close()


def get_reminders(user_id: int):
    conn = get_db_connection()
    sql = sql_query("SELECT id, title, scheduled_at, description, completed FROM reminders WHERE user_id = ? ORDER BY scheduled_at ASC")
    rows = db_execute(conn, sql, (user_id,)).fetchall()
    conn.close()
    return rows


def extract_text_from_file(file_path: str, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        if PdfReader is None:
            raise RuntimeError("pypdf is not installed")
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            # OCR Fallback
            try:
                print("[DEBUG] Entering OCR Fallback...")
                import pymupdf as fitz
                print("[DEBUG] Successfully imported pymupdf")
                import easyocr
                print("[DEBUG] Successfully imported easyocr")
                ocr_text = ""
                doc = fitz.open(file_path)
                print(f"[DEBUG] Opened PDF for OCR: {file_path}, pages: {len(doc)}")
                ocr_reader = easyocr.Reader(['en'], gpu=False)
                print("[DEBUG] Initialized EasyOCR Reader")
                for i, page in enumerate(doc):
                    print(f"[DEBUG] Processing page {i+1}...")
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes('png')
                    result = ocr_reader.readtext(img_bytes, detail=0)
                    print(f"[DEBUG] Page {i+1} OCR result: {result}")
                    ocr_text += "\n".join(result) + "\n"
                if ocr_text.strip():
                    print("[DEBUG] OCR Fallback SUCCESS, text length:", len(ocr_text.strip()))
                    return ocr_text.strip()
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("OCR Fallback Error:", e)
            return "[SCANNED DOCUMENT / IMAGE-ONLY PDF: No embedded text found. Please set a Gemini Vision key in the UI to allow image-based OCR.]"
        return text
    if lower.endswith('.docx'):
        if Document is None:
            raise RuntimeError("python-docx is not installed")
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    if lower.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
            return fh.read()
    raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT")


def store_document(user_id: int, filename: str, content: str):
    conn = get_db_connection()
    sql = sql_query("INSERT INTO knowledge_documents (user_id, filename, content) VALUES (?, ?, ?)")
    db_execute(conn, sql, (user_id, filename, content))
    conn.commit()
    conn.close()


def load_documents(user_id: int):
    conn = get_db_connection()
    sql = sql_query("SELECT filename, content FROM knowledge_documents WHERE user_id = ? ORDER BY created_at DESC")
    rows = db_execute(conn, sql, (user_id,)).fetchall()
    conn.close()
    return [{"filename": row["filename"], "content": row["content"]} for row in rows]


def load_documents_meta(user_id: int):
    conn = get_db_connection()
    sql = sql_query("SELECT id, filename, LENGTH(content) AS char_count, created_at FROM knowledge_documents WHERE user_id = ? ORDER BY created_at DESC")
    rows = db_execute(conn, sql, (user_id,)).fetchall()
    conn.close()
    return [{"id": row["id"], "filename": row["filename"], "char_count": row["char_count"], "created_at": str(row["created_at"])} for row in rows]


def delete_document(user_id: int, doc_id: int):
    conn = get_db_connection()
    sql = sql_query("DELETE FROM knowledge_documents WHERE id = ? AND user_id = ?")
    db_execute(conn, sql, (doc_id, user_id))
    conn.commit()
    conn.close()


init_db()

