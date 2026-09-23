import asyncio
import os
import json
import base64
import time
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from backend.models import *
from backend.database import *

import hashlib
from collections import OrderedDict

try:
    import httpx
except ImportError:
    httpx = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# In-memory LRU cache for TTS audio segments
_TTS_CACHE = OrderedDict()
_MAX_TTS_CACHE_SIZE = 300

def _get_tts_cache(key: str):
    if key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(key)
        return _TTS_CACHE[key]
    return None

def _set_tts_cache(key: str, data: bytes):
    _TTS_CACHE[key] = data
    if len(_TTS_CACHE) > _MAX_TTS_CACHE_SIZE:
        _TTS_CACHE.popitem(last=False)

router = APIRouter()
# We map 'app' to 'router' in the routes lines to minimize changes
app = router

from backend.main import groq_client, gemini_client, gemini_enabled, _use_new_genai, genai_new, genai_legacy, DEFAULT_PROMPT, UPLOAD_DIR, GROQ_API_KEY, WEATHER_API_KEY, get_groq_client

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    return FileResponse(frontend_path)

@app.post("/signup")
def signup(req: SignupRequest, response: Response):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    conn = get_db_connection()
    sql = sql_query("SELECT id FROM users WHERE username = ?")
    existing = db_execute(conn, sql, (req.username.strip(),)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # New user signups default to is_approved = 1 (automatically approved)
    insert_sql = (
        sql_query("INSERT INTO users (username, password_hash, is_approved) VALUES (?, ?, TRUE) RETURNING id")
        if DATABASE_URL
        else sql_query("INSERT INTO users (username, password_hash, is_approved) VALUES (?, ?, 1)")
    )

    cursor = db_execute(conn, insert_sql, (req.username.strip(), hash_password(req.password)))
    if DATABASE_URL:
        row = cursor.fetchone()
        user_id = row["id"] if row and "id" in row else None
    else:
        user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if user_id:
        save_preferences(user_id, lang="en", tts_enabled=True, voice_input_enabled=True)
        
    session_id = create_session(user_id) if user_id else None
    
    response = JSONResponse({
        "ok": True, 
        "pending": False,
        "username": req.username.strip(), 
        "message": "Registration successful! You can now access the AI."
    })
    
    if session_id:
        response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
        
    return response

@app.post("/login")
def login(req: LoginRequest, response: Response):
    conn = get_db_connection()
    sql = sql_query("SELECT id, username, password_hash, is_approved FROM users WHERE username = ?")
    row = db_execute(conn, sql, (req.username.strip(),)).fetchone()
    conn.close()
    if not row or not verify_password(row["password_hash"], req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not bool(row["is_approved"]):
        raise HTTPException(status_code=403, detail="Account access disabled or pending Admin approval.")
        
    session_id = create_session(row["id"])
    response = JSONResponse({"ok": True, "username": row["username"], "message": "Logged in successfully"})
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response

@app.post("/logout")
def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        conn = get_db_connection()
        sql = sql_query("DELETE FROM sessions WHERE id = ?")
        db_execute(conn, sql, (session_id,))
        conn.commit()
        conn.close()
    response = JSONResponse({"ok": True, "message": "Logged out"})
    response.delete_cookie("session_id")
    return response

@app.get("/me")
def me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    prefs = get_preferences(user["id"])
    return {"ok": True, "username": user["username"], "is_admin": user.get("is_admin", False), "preferences": prefs}

@app.post("/preferences")
def preferences(req: PreferencesRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    save_preferences(user["id"], lang=req.lang, tts_enabled=req.tts_enabled, voice_input_enabled=req.voice_input_enabled)
    return get_preferences(user["id"])

@app.get("/reminders")
def get_user_reminders(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    rows = get_reminders(user["id"])
    reminders = [
        {
            "id": row["id"],
            "title": row["title"],
            "scheduled_at": str(row["scheduled_at"]),
            "description": row["description"],
            "completed": bool(row["completed"]),
        }
        for row in rows
    ]
    return {"reminders": reminders}

@app.post("/reminders")
def create_reminder(req: ReminderRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    add_reminder(user["id"], req.title, req.scheduled_at, req.description)
    log_event(user["id"], "reminder_created", req.title)
    return {"ok": True, "message": "Reminder created"}

@app.post("/reminders/{reminder_id}/complete")
def complete_reminder_route(reminder_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    complete_reminder(user["id"], reminder_id)
    log_event(user["id"], "reminder_completed", str(reminder_id))
    return {"ok": True, "message": "Reminder marked complete"}

@app.post("/analytics/event")
def analytics_event(req: AnalyticsEventRequest, request: Request):
    user = get_current_user(request)
    log_event(user["id"] if user else None, req.event_type, req.metadata)
    return {"ok": True, "message": "Event logged"}

@app.get("/admin/analytics")
def admin_analytics():
    conn = get_db_connection()
    sql = sql_query("SELECT event_type, COUNT(*) AS event_count FROM analytics GROUP BY event_type ORDER BY event_count DESC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql).fetchall()
        conn.close()
    return {"analytics": [{"event_type": row["event_type"], "count": int(row["event_count"])} for row in rows]}

class AdminAddUserRequest(BaseModel):
    username: str
    password: str

@app.get("/admin/users")
def get_admin_users(request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    sql = sql_query("SELECT id, username, is_admin, is_approved, created_at FROM users ORDER BY is_approved ASC, id DESC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql).fetchall()
        conn.close()
    users = [{
        "id": r["id"], 
        "username": r["username"], 
        "is_admin": bool(r["is_admin"]), 
        "is_approved": bool(r["is_approved"]),
        "created_at": str(r["created_at"])
    } for r in rows]
    return {"users": users}

@app.post("/admin/users/{user_id}/approve")
def admin_approve_user(user_id: int, request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    sql = sql_query("UPDATE users SET is_approved = 1 WHERE id = ?")
    db_execute(conn, sql, (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "User access request approved successfully!"}

@app.post("/admin/users")
def admin_add_user(req: AdminAddUserRequest, request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    conn = get_db_connection()
    sql = sql_query("SELECT id FROM users WHERE username = ?")
    existing = db_execute(conn, sql, (req.username.strip(),)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    insert_sql = sql_query("INSERT INTO users (username, password_hash, is_approved) VALUES (?, ?, 1)")
    db_execute(conn, insert_sql, (req.username.strip(), hash_password(req.password)))
    conn.commit()
    conn.close()
    return {"ok": True, "message": f"User '{req.username.strip()}' created and approved successfully"}

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    conn = get_db_connection()
    sql = sql_query("DELETE FROM users WHERE id = ?")
    db_execute(conn, sql, (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "User deleted successfully"}

@app.get("/admin/users/{user_id}/threads")
def admin_get_user_threads(user_id: int, request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    sql = sql_query("SELECT id, title, pinned, archived, updated_at, created_at FROM chat_threads WHERE user_id = ? ORDER BY updated_at DESC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql, (user_id,)).fetchall()
        conn.close()
    threads = [{
        "id": r["id"], "title": r["title"], 
        "pinned": bool(r["pinned"]), "archived": bool(r["archived"]),
        "updated_at": str(r["updated_at"]), "created_at": str(r["created_at"])
    } for r in rows]
    return {"threads": threads}

@app.get("/admin/users/{user_id}/threads/{thread_id}")
def admin_get_user_thread_messages(user_id: int, thread_id: str, request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db_connection()
    
    # Verify the thread belongs to the requested user
    check_sql = sql_query("SELECT 1 FROM chat_threads WHERE id = ? AND user_id = ?")
    exists = db_execute(conn, check_sql, (thread_id, user_id)).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Thread not found for this user")
        
    sql = sql_query("SELECT id, role, content, image_url, created_at FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql, (thread_id,))
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql, (thread_id,)).fetchall()
        conn.close()
    messages = [{
        "id": r["id"], "role": r["role"], "content": r["content"],
        "image_url": r["image_url"], "created_at": str(r["created_at"])
    } for r in rows]
    return {"messages": messages}


class ThreadCreateRequest(BaseModel):
    title: str
    id: str

class ThreadUpdateRequest(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None

@app.get("/api/threads")
def get_threads(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    sql = sql_query("SELECT id, title, pinned, archived, updated_at, created_at FROM chat_threads WHERE user_id = ? ORDER BY updated_at DESC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql, (user["id"],))
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql, (user["id"],)).fetchall()
        conn.close()
    threads = []
    for r in rows:
        threads.append({
            "id": r["id"], "title": r["title"], 
            "pinned": bool(r["pinned"]), "archived": bool(r["archived"]),
            "updated_at": str(r["updated_at"]), "created_at": str(r["created_at"])
        })
    return {"threads": threads}

@app.post("/api/threads")
def create_thread(req: ThreadCreateRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    sql = sql_query("INSERT INTO chat_threads (id, user_id, title) VALUES (?, ?, ?)")
    db_execute(conn, sql, (req.id, user["id"], req.title))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/threads/{thread_id}")
def get_thread_messages(thread_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    sql = sql_query("SELECT id, role, content, image_url, created_at FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql, (thread_id,))
            rows = cur.fetchall()
        conn.close()
    else:
        rows = db_execute(conn, sql, (thread_id,)).fetchall()
        conn.close()
    messages = []
    for r in rows:
        messages.append({
            "id": r["id"], "role": r["role"], "content": r["content"],
            "image_url": r["image_url"], "created_at": str(r["created_at"])
        })
    return {"messages": messages}

@app.delete("/api/threads/{thread_id}")
def delete_thread(thread_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    sql = sql_query("DELETE FROM chat_threads WHERE id = ? AND user_id = ?")
    db_execute(conn, sql, (thread_id, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/clear-history")
def clear_all_history(request: Request):
    user = get_current_user(request)
    conn = get_db_connection()
    if user:
        db_execute(conn, sql_query("DELETE FROM chat_threads WHERE user_id = ?"), (user["id"],))
        db_execute(conn, sql_query("DELETE FROM conversations WHERE user_id = ?"), (user["id"],))
        db_execute(conn, sql_query("DELETE FROM knowledge_documents WHERE user_id = ?"), (user["id"],))
    else:
        db_execute(conn, "DELETE FROM chat_threads")
        db_execute(conn, "DELETE FROM chat_messages")
        db_execute(conn, "DELETE FROM conversations")
        db_execute(conn, "DELETE FROM knowledge_documents")
    conn.commit()
    conn.close()
    return {"ok": True, "message": "All history cleared successfully"}

@app.put("/api/threads/{thread_id}")
def update_thread(thread_id: str, req: ThreadUpdateRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    if req.title is not None:
        sql = sql_query("UPDATE chat_threads SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?")
        db_execute(conn, sql, (req.title, thread_id, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/upload-chat-image")
def upload_chat_image(file: UploadFile = File(...)):
    filename = file.filename or "image.jpg"
    safe_name = filename.replace("/", "_").replace("\\", "_")
    uniq_name = f"{uuid.uuid4().hex}_{safe_name}"
    path = os.path.join(UPLOAD_DIR, uniq_name)
    with open(path, "wb") as fh:
        fh.write(file.file.read())
    return {"url": f"/uploads/{uniq_name}"}

def save_chat_message(user_id: int, thread_id: str, role: str, content: str, image_url: Optional[str] = None):
    if not thread_id: return
    conn = get_db_connection()
    try:
        sql_check = sql_query("SELECT 1 FROM chat_threads WHERE id = ?")
        existing = db_execute(conn, sql_check, (thread_id,)).fetchone()
        if not existing and user_id:
            first_words = (content or "New Conversation").split()[:5]
            title = " ".join(first_words) if first_words else "New Conversation"
            sql_ins = sql_query("INSERT INTO chat_threads (id, user_id, title) VALUES (?, ?, ?)")
            db_execute(conn, sql_ins, (thread_id, user_id, title))
        
        sql = sql_query("INSERT INTO chat_messages (thread_id, role, content, image_url) VALUES (?, ?, ?, ?)")
        db_execute(conn, sql, (thread_id, role, content, image_url))
        sql_update = sql_query("UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?")
        db_execute(conn, sql_update, (thread_id,))
        conn.commit()
    finally:
        conn.close()


@app.get("/history")
def history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    conn = get_db_connection()
    sql = sql_query("SELECT role, content, created_at FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT 30")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql, (user["id"],))
            rows = cur.fetchall()
        conn.close()
        conversations = [{"role": row["role"], "content": row["content"], "created_at": str(row["created_at"])} for row in rows]
    else:
        rows = db_execute(conn, sql, (user["id"],)).fetchall()
        conn.close()
        conversations = [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]
    return {"conversations": conversations}

@app.post("/upload")
def upload_document(request: Request, file: UploadFile = File(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")

    filename = file.filename or "document"
    safe_name = filename.replace("/", "_").replace("\\", "_")
    path = os.path.join(UPLOAD_DIR, f"{user['id']}_{uuid.uuid4().hex}_{safe_name}")
    with open(path, "wb") as fh:
        fh.write(file.file.read())

    try:
        text = extract_text_from_file(path, safe_name)
        if not text or not text.strip():
            if os.path.exists(path): os.remove(path)
            raise HTTPException(status_code=400, detail="Uploaded document contains no readable text")
    except HTTPException:
        if os.path.exists(path): os.remove(path)
        raise
    except Exception as e:
        if os.path.exists(path): os.remove(path)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    store_document(user["id"], safe_name, text)
    log_event(user["id"], "document_uploaded", safe_name)
    return {"ok": True, "filename": safe_name, "message": "Document uploaded successfully"}

@app.get("/documents")
def list_user_documents(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    docs = load_documents_meta(user["id"])
    return {"documents": docs}

@app.delete("/documents/{doc_id}")
def delete_user_document(doc_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    delete_document(user["id"], doc_id)
    log_event(user["id"], "document_deleted", str(doc_id))
    return {"ok": True, "message": "Document deleted successfully"}

def build_context_text(docs, max_chars=2000):
    context = ""
    for doc in docs:
        doc_text = f"Document: {doc['filename']}\n{doc['content']}\n\n"
        if len(context) + len(doc_text) > max_chars:
            remaining = max_chars - len(context)
            if remaining > 100:
                context += doc_text[:remaining] + "...[truncated]"
            break
        context += doc_text
    return context

import re

def strip_markdown_for_tts(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[*_~`#]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# ── HuggingFace BLIP Vision ──────────────────────────────────────────────────
def call_huggingface_blip(img, user_prompt=""):
    """Call HuggingFace BLIP-2 API for real image captioning/VQA. Free, no key needed."""
    try:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        image_bytes = buf.read()

        # Use BLIP image-to-text (free tier, no auth required for small requests)
        headers = {"Content-Type": "application/octet-stream"}
        hf_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
        response = httpx.post(hf_url, content=image_bytes, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                caption = result[0].get("generated_text", "").strip()
                if caption:
                    return caption
    except Exception as e:
        print(f"HuggingFace BLIP error: {e}")
    return ""


def call_huggingface_vqa(img, question="What is in this image?"):
    """Call HuggingFace VQA model for question answering about image."""
    try:
        import json as _json
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        image_b64 = base64.b64encode(buf.read()).decode("utf-8")

        payload = {"inputs": {"image": image_b64, "question": question}}
        hf_url = "https://api-inference.huggingface.co/models/dandelin/vilt-b32-finetuned-vqa"
        response = httpx.post(hf_url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0].get("answer", "").strip()
    except Exception as e:
        print(f"HuggingFace VQA error: {e}")
    return ""


def analyze_pil_image_attributes(img):
    if not img:
        return ""
    try:
        from PIL import ImageStat
        width, height = img.size
        aspect_ratio = width / height
        if aspect_ratio > 1.3:
            orientation = "Landscape (Widescreen)"
        elif aspect_ratio < 0.77:
            orientation = "Portrait (Vertical)"
        else:
            orientation = "Square"
            
        stat = ImageStat.Stat(img)
        r, g, b = stat.mean[:3]
        brightness = (0.299*r + 0.587*g + 0.114*b)
        if brightness < 60:
            tone = "Sleek Dark Mode / Low-Light Atmospheric Tone"
        elif brightness > 190:
            tone = "High-Key Vibrant / Bright Daylight Tone"
        else:
            tone = "Balanced Medium Contrast Tone"
            
        fmt = getattr(img, "format", "JPEG") or "JPEG"
        return (
            f"\n\n[Visual Asset Parameters:\n"
            f"- Aspect & Dimensions: {width}x{height} pixels ({orientation})\n"
            f"- Asset Format: {fmt}\n"
            f"- Lighting & Ambiance: {tone} (Luminance: {brightness:.1f}/255)\n"
            f"- Color Balance: RGB({int(r)}, {int(g)}, {int(b)})]"
        )

    except Exception as e:
        return f"\n\n[Attached Image Asset: {img.size[0]}x{img.size[1]}px]"


def generate_fallback_vision_report(img, user_prompt="", blip_caption=""):
    """Generate a rich vision analysis report, using BLIP caption if available."""
    if not img:
        return "✦ **Visual Analysis**: No image file attached."
    try:
        from PIL import ImageStat
        width, height = img.size
        aspect_ratio = width / height
        if aspect_ratio > 1.3:
            orientation = "Landscape Widescreen (16:9 Aspect)"
        elif aspect_ratio < 0.77:
            orientation = "Portrait Vertical (9:16 Aspect)"
        else:
            orientation = "Square (1:1 Aspect)"

        stat = ImageStat.Stat(img)
        r, g, b = stat.mean[:3]
        brightness = (0.299*r + 0.587*g + 0.114*b)

        if brightness < 55:
            lighting = "Sleek Dark Mode / Atmospheric Low-Light Tone"
        elif brightness > 185:
            lighting = "High-Key Vibrant / Bright Daylight Ambiance"
        else:
            lighting = "Balanced Medium Contrast & Studio Lighting"

        fmt = getattr(img, "format", "JPEG") or "JPEG"

        dominant_colors = []
        if r > g and r > b:
            dominant_colors.append("Crimson / Warm Red Spectrum")
        if g > r and g > b:
            dominant_colors.append("Emerald Green Tones")
        if b > r and b > g:
            dominant_colors.append("Midnight Indigo / Cool Cyan Blues")
        if abs(r-g) < 25 and abs(g-b) < 25:
            if brightness < 80:
                dominant_colors.append("Charcoal Black & Deep Gothic Shadows")
            else:
                dominant_colors.append("Clean White & Slate Grey Elements")

        colors_str = ", ".join(dominant_colors) if dominant_colors else "Harmonized RGB Spectrum"

        ocr_text = ""
        try:
            import pytesseract
            ocr_text = pytesseract.image_to_string(img).strip()
        except Exception:
            pass

        text_section = f"\n\n**Extracted Text & Symbols:**\n```\n{ocr_text}\n```" if ocr_text else ""

        # Include real BLIP caption if we have one
        ai_section = ""
        if blip_caption:
            ai_section = f"\n\n**🤖 AI Object & Scene Recognition:**\n- {blip_caption.capitalize()}."

        report = (
            f"✦ **Mikey Vision Analysis**{ai_section}\n\n"
            f"**📐 Image Dimensions & Format:**\n"
            f"- Resolution: {width}×{height} pixels ({orientation})\n"
            f"- Format: {fmt}\n\n"
            f"**🌅 Lighting & Ambiance:**\n"
            f"- {lighting} (Luminance: {brightness:.1f}/255)\n\n"
            f"**🎨 Color Palette:**\n"
            f"- Dominant Tones: {colors_str}\n"
            f"- RGB Profile: R={int(r)}, G={int(g)}, B={int(b)}"
            f"{text_section}"
        )

        return report
    except Exception as e:
        return f"✦ **Visual Breakdown**: Image processed ({img.size[0]}x{img.size[1]}px)."


def call_ai_chat(prompt_or_messages, system_instruction=DEFAULT_PROMPT, history=None, image_url=None, is_doc_task=False):
    loaded_img = None
    blip_caption = ""

    if image_url:
        loaded_img = load_pil_image(image_url)
        system_instruction += (
            "\n\nOperating Mode: Multimodal Vision Analyst. "
            "You have been provided with a real image. NEVER state you cannot view images. "
            "Describe everything visible: objects, people, colors, background, text, style, and mood."
        )


    # ── Step 0: Bypass HuggingFace BLIP (Network Blocked) ──
    if loaded_img and not gemini_enabled:
        # HuggingFace is currently unreachable on this host (getaddrinfo failed).
        # We will natively process the image using the multimodal API below instead.
        blip_caption = ""

    # ── Step 1: Try Gemini first if enabled (best vision quality) ────────────────
    if gemini_enabled and gemini_client:
        try:
            if _use_new_genai and isinstance(gemini_client, type(genai_new.Client(api_key="x"))) if genai_new else False:
                # New google-genai SDK
                if is_doc_task:
                    resp = gemini_client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=prompt_or_messages,
                        config={"system_instruction": system_instruction}
                    )

                    return resp.text
                else:
                    parts = []
                    if loaded_img:
                        buf = BytesIO()
                        loaded_img.save(buf, format="JPEG")
                        buf.seek(0)
                        parts.append(genai_types.Part.from_bytes(data=buf.read(), mime_type="image/jpeg"))
                    user_question = prompt_or_messages if isinstance(prompt_or_messages, str) and prompt_or_messages \
                        else "Analyze and describe everything you see in this image in full detail."
                    parts.append(user_question)
                    resp = gemini_client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=parts,
                        config={"system_instruction": system_instruction}
                    )

                    reply = resp.text
            else:
                # Legacy google.generativeai SDK
                genai = gemini_client
                model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
                if is_doc_task:
                    res = model.generate_content(prompt_or_messages)
                    return res.text
                else:
                    contents = []
                    if history:
                        for h in history[-10:]:
                            role = "model" if h.get("role") in ["assistant", "model"] else "user"
                            content = h.get("content", "")
                            if content and not any(phrase in content.lower() for phrase in
                                                   ["text-based mode", "cannot directly access",
                                                    "do not have the capability", "unable to view"]):
                                contents.append({"role": role, "parts": [content]})
                    user_parts = []
                    if loaded_img:
                        user_parts.append(loaded_img)
                    user_question = prompt_or_messages if isinstance(prompt_or_messages, str) and prompt_or_messages \
                        else "Analyze and describe everything you see in this image in full detail."
                    user_parts.append(user_question)
                    contents.append({"role": "user", "parts": user_parts})
                    res = model.generate_content(contents)
                    reply = res.text
            if reply and not any(phrase in reply.lower() for phrase in
                                 ["text-based mode", "cannot directly access",
                                  "unable to view", "cannot view"]):
                return reply
        except Exception as gem_err:
            print(f"Gemini error, falling back: {gem_err}")

    # ── Step 2: Use multimodal custom proxy (Groq client) ───────────────────────────────────────────────
    if groq_client:
        try:
            if is_doc_task:
                res = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt_or_messages}
                    ],
                    max_tokens=1000,
                    temperature=0.4,
                )

                return res.choices[0].message.content
            else:
                messages = [{"role": "system", "content": system_instruction}]
                if history:
                    for h in history[-4:]:
                        content = h.get("content", "")
                        if content and not any(phrase in content.lower() for phrase in
                                               ["text-based mode", "cannot directly access",
                                                "do not have the capability", "unable to view", "groq api error"]):
                            messages.append({"role": h.get("role", "user"), "content": content})

                user_msg = prompt_or_messages if isinstance(prompt_or_messages, str) and prompt_or_messages \
                    else "Describe and analyze the image in detail."

                model_to_use = "qwen/qwen3.8-27b"
                if image_url:
                    model_to_use = "qwen/qwen3.8-27b"
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_msg},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": user_msg})

                res = groq_client.chat.completions.create(
                    model=model_to_use,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.6,
                )

                reply = res.choices[0].message.content

                # Refusal interceptor
                refusal_phrases = [
                    "text-based mode", "cannot directly access", "unable to view",
                    "cannot view", "cannot process external images", "do not have the capability",
                    "i'm unable to access", "i cannot access", "as a text-based"
                ]
                if not reply or any(phrase in reply.lower() for phrase in refusal_phrases):
                    if loaded_img:
                        return generate_fallback_vision_report(loaded_img, str(prompt_or_messages), blip_caption)
                    return "Mikey is ready. Please type your message."
                return reply
        except Exception as groq_err:
            print(f"Groq API (Vision fallback) error: {groq_err}")
            if not loaded_img:
                return f"Groq API Error: {groq_err}"

    # ── Step 3: BLIP + pixel fallback report ─────────────────────────────────────
    if loaded_img:
        return generate_fallback_vision_report(loaded_img, str(prompt_or_messages), blip_caption)

    return "System Error: The AI provider is temporarily unavailable or out of quota."


# ── Neural Link Announce Queue ───────────────────────────────────────────────
# In-memory queue for system announcements injected into the chatbot UI
import collections
_announce_queue = collections.deque(maxlen=50)

class AnnounceRequest(BaseModel):
    phase: str   # "plan" | "complete" | "error" | "info"
    message: str

@app.post("/api/announce")
def post_announce(req: AnnounceRequest):
    """Inject a system message into the Neural Link chat from Antigravity."""
    _announce_queue.append({"phase": req.phase, "message": req.message, "ts": time.time()})
    return {"ok": True}

@app.get("/api/poll-announce")
def poll_announce(since: float = 0):
    """Frontend polls this to retrieve new system messages."""
    new_msgs = [m for m in _announce_queue if m["ts"] > since]
    return {"messages": new_msgs}

class KeyRequest(BaseModel):
    api_key: str

@app.post("/api/save-gemini-key")
def save_gemini_key(req: KeyRequest):
    global GEMINI_API_KEY, gemini_enabled
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty")
    
    try:
        success = _init_gemini(key)
        if not success:
            raise Exception("Gemini key verification failed or API unreachable")
        GEMINI_API_KEY = key
        
        env_path = ".env"
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()
        
        updated = False
        new_lines = []
        for line in env_lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}\n")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"GEMINI_API_KEY={key}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        return {"ok": True, "message": "Gemini Multimodal AI Vision activated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gemini key verification failed: {str(e)}")

@app.post("/ask-knowledge")
def ask_knowledge(request: Request, question: str = Form(...)):
    try:
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not signed in")

        docs = load_documents(user["id"])
        if not docs:
            raise HTTPException(status_code=404, detail="No uploaded documents found")

        context_text = build_context_text(docs, max_chars=2000)
        prompt = f"Use the following document context to answer the user's question. If the answer is not in the context, say you do not know.\n\nContext:\n{context_text}\n\nQuestion:\n{question}"
        
        reply = call_ai_chat(prompt, system_instruction="You answer using the uploaded document context.", is_doc_task=True)
        return {"answer": reply}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge Ask Error: {str(e)}")

@app.post("/analyze-documents")
def analyze_documents(request: Request):
    try:
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not signed in")

        docs = load_documents(user["id"])
        if not docs:
            raise HTTPException(status_code=404, detail="No uploaded documents found to analyze")

        context_text = build_context_text(docs, max_chars=2000)
        prompt = f"Please provide a very brief, high-level overview (1-2 sentences max) of what these documents are about, and then ask the user what specific questions they have about the content. Do not provide a long, comprehensive summary of every section or paper.\n\nDocuments:\n{context_text}"
        
        analysis = call_ai_chat(prompt, system_instruction="You are a helpful and friendly tutor. Give a very brief overview of the provided documents and ask the user how you can help them navigate the specific details. Be conversational like ChatGPT or Claude.", is_doc_task=True)
        return {"analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")

@app.get("/admin/stats")
def admin_stats():
    conn = get_db_connection()
    sql_users = sql_query("SELECT COUNT(*) AS user_count FROM users")
    sql_conv = sql_query("SELECT COUNT(*) AS conversation_count FROM conversations")
    sql_reminders = sql_query("SELECT COUNT(*) AS reminder_count FROM reminders")
    sql_analytics = sql_query("SELECT COUNT(*) AS analytics_count FROM analytics")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute(sql_users)
            user_count = cur.fetchone()["user_count"]
            cur.execute(sql_conv)
            conversation_count = cur.fetchone()["conversation_count"]
            cur.execute(sql_reminders)
            reminder_count = cur.fetchone()["reminder_count"]
            cur.execute(sql_analytics)
            analytics_count = cur.fetchone()["analytics_count"]
        conn.close()
    else:
        user_count = db_execute(conn, sql_users).fetchone()["user_count"]
        conversation_count = db_execute(conn, sql_conv).fetchone()["conversation_count"]
        reminder_count = db_execute(conn, sql_reminders).fetchone()["reminder_count"]
        analytics_count = db_execute(conn, sql_analytics).fetchone()["analytics_count"]
        conn.close()
    return {
        "user_count": user_count,
        "conversation_count": conversation_count,
        "reminder_count": reminder_count,
        "analytics_count": analytics_count,
        "status": "ready"
    }

def load_pil_image(image_url: str):
    if not image_url:
        return None
    try:
        from PIL import Image
        img_obj = None
        if image_url.startswith("/uploads/") or image_url.startswith("uploads/"):
            filename = image_url.split("/")[-1]
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                img_obj = Image.open(filepath)
        elif image_url.startswith("data:image"):
            import base64
            header, encoded = image_url.split(",", 1)
            data = base64.b64decode(encoded)
            img_obj = Image.open(BytesIO(data))
        elif image_url.startswith("http://") or image_url.startswith("https://"):
            import httpx
            r = httpx.get(image_url, timeout=10)
            if r.status_code == 200:
                img_obj = Image.open(BytesIO(r.content))

        if img_obj:
            converted = img_obj.convert("RGB")
            converted.load()
            return converted
    except Exception as e:
        print(f"Image load error: {e}")
    return None

import urllib.parse
import xml.etree.ElementTree as ET
import httpx
import datetime
from concurrent.futures import ThreadPoolExecutor

def get_dynamic_temporal_context() -> str:
    """Generates an accurate present-day temporal anchor for the system prompt."""
    now = datetime.datetime.now()
    weekday = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    return (
        f"[SYSTEM TEMPORAL ANCHOR & REAL-TIME GROUNDING]\n"
        f"• Operating Date: {weekday}, {date_str}\n"
        f"• Operating Time: {time_str}\n"
        f"• Operating Year: {now.year}\n"
        f"• Active Status: You are connected to Mikey's active real-time web retrieval pipeline.\n"
        f"• Directive: Answer with present-day facts as of {now.year}. Never state that you have a knowledge cutoff or lack real-time access."
    )

def universal_intent_router(msg: str):
    """Categorizes the user request, detects language, and selects appropriate real-time data pipeline."""
    if not msg:
        return {"intent": "GENERAL", "language": "en", "requires_live_data": False, "category": "general", "query": ""}
    
    msg_lower = msg.lower().strip()
    
    # 1. Language Detection
    import re
    lang = "te" if re.search(r'[\u0C00-\u0C7F]', msg_lower) else "en"
    
    # 2. Weather Detection
    if any(w in msg_lower for w in ["weather", "temperature", "forecast", "climate", "raining", "rain", "వాతావరణం"]):
        city_match = re.search(r'(?:in|for|at|around)\s+([a-zA-Z\s]+)', msg_lower)
        city = city_match.group(1).strip() if city_match else msg.strip()
        return {"intent": "WEATHER", "language": lang, "requires_live_data": True, "category": "weather", "query": city}

    # 3. Explicit Time, Current, & Recency Indicators
    time_terms = [
        "today", "latest", "this week", "the week", "of the week", "recent", "recently", "breaking",
        "currently", "now", "new", "this season", "rankings", "update", "updates", "upcoming",
        "schedule", "premiere", "premiering", "airing", "released", "dropped", "this year", "this month",
        "yesterday", "tonight", "tomorrow", "present", "ongoing", "status", "developments",
        "what's going on", "what's happening", "whats going on", "whats happening", "what is happening",
        "what happened", "who won", "winner of", "standings", "leaderboard",
        "who is the current", "who is currently", "who is ceo", "who is president", "who is prime minister",
        "2024", "2025", "2026", "2027",
        "news", "headlines", "scores", "score", "match", "matches", "tournament",
        "stock price", "crypto price", "price of", "market cap",
        "knowledge cutoff", "cutoff date", "real-time awareness",
        "ఈరోజు", "ఈ వారం", "తాజా", "ప్రస్తుతం", "కొత్తగా", "కొత్త", "వార్తలు", "అప్‌డేట్", "అప్‌డేట్స్", "ఫలితాలు", "ధర"
    ]
    has_time = any(t in msg_lower for t in time_terms)

    # 4. Categories & Intent Resolution
    if any(t in msg_lower for t in ["anime", "అనిమే"]):
        if has_time or any(t in msg_lower for t in ["news", "releases", "release", "airing", "rankings", "season", "update", "updates", "new", "upcoming", "dropped", "వార్తలు"]):
            return {"intent": "ANIME_CURRENT", "language": lang, "requires_live_data": True, "category": "anime", "query": f"latest anime release {msg}"}
        return {"intent": "ANIME_RECOMMENDATION", "language": lang, "requires_live_data": False, "category": "anime", "query": msg}
        
    if any(t in msg_lower for t in ["study", "focus", "retain", "exam", "memorize", "చదువు", "చదవాలి", "పరీక్ష"]):
        return {"intent": "STUDY", "language": lang, "requires_live_data": False, "category": "study", "query": msg}
        
    if any(t in msg_lower for t in ["health", "nutrition", "exercise", "sleep", "fitness", "ఆరోగ్య", "హెల్త్", "బరువు", "నిద్ర"]):
        if has_time or any(t in msg_lower for t in ["news", "వార్తలు", "update", "updates"]):
            return {"intent": "HEALTH_NEWS", "language": lang, "requires_live_data": True, "category": "health", "query": f"health {msg}"}
        return {"intent": "HEALTH", "language": lang, "requires_live_data": False, "category": "health", "query": msg}
        
    if any(t in msg_lower for t in ["sports", "cricket", "football", "tennis", "basketball", "క్రీడా", "స్పోర్ట్స్", "క్రికెట్", "మ్యాచ్"]):
        query = "cricket" if "cricket" in msg_lower or "క్రికెట్" in msg_lower else ("football" if "football" in msg_lower else "sports")
        return {"intent": "SPORTS_NEWS", "language": lang, "requires_live_data": True, "category": "sports", "query": f"{query} {msg}" if has_time else query}
        
    if any(t in msg_lower for t in ["technology", "tech", "ai", "openai", "smartphone", "gpu", "nvidia", "apple", "google", "meta", "model", "టెక్నాలజీ"]):
        if has_time or any(t in msg_lower for t in ["news", "updates", "update", "release", "releases", "announcement"]):
            return {"intent": "TECHNOLOGY_NEWS", "language": lang, "requires_live_data": True, "category": "technology", "query": f"technology {msg}"}
        return {"intent": "TECHNOLOGY_GENERAL", "language": lang, "requires_live_data": False, "category": "technology", "query": msg}
        
    if any(t in msg_lower for t in ["business", "stock", "market", "startup", "economy", "crypto", "bitcoin", "వ్యాపారం"]):
        return {"intent": "BUSINESS_NEWS", "language": lang, "requires_live_data": True, "category": "business", "query": msg}
        
    if any(t in msg_lower for t in ["movie", "entertainment", "box office", "సినిమా", "సినిమాలు", "film"]):
        if has_time or any(t in msg_lower for t in ["news", "releases", "reviews", "review", "updates", "update"]):
            return {"intent": "ENTERTAINMENT_NEWS", "language": lang, "requires_live_data": True, "category": "entertainment", "query": f"latest movies {msg}"}
        return {"intent": "ENTERTAINMENT_GENERAL", "language": lang, "requires_live_data": False, "category": "entertainment", "query": msg}

    if any(t in msg_lower for t in ["news", "headlines", "వార్తలు"]):
        return {"intent": "LIVE_NEWS", "language": lang, "requires_live_data": True, "category": "general", "query": "news"}
        
    if has_time:
        return {"intent": "LIVE_SEARCH", "language": lang, "requires_live_data": True, "category": "live_web", "query": msg}

    return {"intent": "GENERAL", "language": lang, "requires_live_data": False, "category": "general", "query": msg}

def fetch_weather_direct(city: str) -> list:
    """Fetch live meteorological conditions from wttr.in without requiring an API key."""
    try:
        clean_city = urllib.parse.quote(city.strip())
        url = f"https://wttr.in/{clean_city}?format=j1"
        with httpx.Client(timeout=4.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                data = r.json()
                cur = data["current_condition"][0]
                temp_c = cur.get("temp_C", "")
                desc = cur.get("weatherDesc", [{}])[0].get("value", "")
                humidity = cur.get("humidity", "")
                wind = cur.get("windspeedKmph", "")
                return [{
                    "title": f"Current Weather in {city.title()}",
                    "source": f"Live Weather Feed: {temp_c}°C ({desc}), Humidity: {humidity}%, Wind: {wind} km/h.",
                    "snippet": f"The temperature in {city.title()} is {temp_c}°C with {desc}. Humidity is at {humidity}%, with winds around {wind} km/h.",
                    "pubDate": "Real-Time Sensor Feed",
                    "link": f"https://wttr.in/{clean_city}"
                }]
    except Exception as e:
        print(f"Weather fetch error: {e}")
    return []

def fetch_deep_snippet(url: str, max_chars: int = 700) -> str:
    """Extract clean body text from a webpage using BeautifulSoup."""
    if not url or not url.startswith("http"):
        return ""
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=2.8, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 40]
            if paragraphs:
                return " ".join(paragraphs)[:max_chars]
    except Exception:
        pass
    return ""

def fetch_wikipedia_search(query: str, max_results: int = 3) -> list:
    """Fetch factual background and current event updates from Wikipedia API."""
    try:
        import requests
        headers = {"User-Agent": "MikeyAI/1.0 (contact@mikey.ai)"}
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "utf8": 1, "srlimit": max_results},
            headers=headers,
            timeout=3.0
        )
        if r.status_code == 200:
            items = r.json().get("query", {}).get("search", [])
            results = []
            for it in items:
                title = it.get("title", "")
                snippet = it.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                clean_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({
                    "title": title,
                    "source": "Wikipedia",
                    "snippet": snippet,
                    "pubDate": "Wikipedia Knowledge Base",
                    "link": clean_url
                })
            return results
    except Exception as e:
        print(f"Wikipedia search error: {e}")
    return []

def fetch_google_news_rss(query: str, lang: str = 'en', max_items: int = 4) -> list:
    """Fetch live news from Google News RSS with fast concurrent decoding."""
    try:
        import requests
        from googlenewsdecoder import new_decoderv1

        hl = 'te' if lang == 'te' else 'en-IN'
        gl = 'IN'
        encoded_q = urllib.parse.quote(query)
        url = f'https://news.google.com/rss/search?q={encoded_q}&hl={hl}&gl={gl}&ceid={gl}:{hl}'

        r = requests.get(url, timeout=5.0)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        items = root.findall('.//item')[:max_items]
        if not items:
            return []

        def decode_item(it):
            title = it.findtext('title', '')
            pub_date = it.findtext('pubDate', '')
            source = it.find('source')
            source_name = source.text if source is not None else 'News Source'
            raw_link = it.findtext('link', '')
            clean_link = raw_link
            try:
                dec = new_decoderv1(raw_link)
                if dec.get("status") and dec.get("decoded_url"):
                    clean_link = dec["decoded_url"]
            except Exception:
                pass
            return {
                "title": title,
                "source": source_name,
                "snippet": f"Reported by {source_name}: {title}",
                "pubDate": pub_date,
                "link": clean_link
            }

        with ThreadPoolExecutor(max_workers=min(4, len(items))) as executor:
            return list(executor.map(decode_item, items))
    except Exception as e:
        print(f"Google News RSS error: {e}")
        return []

def fetch_duckduckgo_news_or_text(query: str, max_results: int = 4) -> list:
    """Fetch live search from DuckDuckGo with Ratelimit safety."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            try:
                news_items = list(ddgs.news(query, max_results=max_results))
                for n in news_items:
                    results.append({
                        "title": n.get("title", ""),
                        "source": n.get("source", "Live Web"),
                        "snippet": n.get("body", "")[:350],
                        "pubDate": n.get("date", "Live Web"),
                        "link": n.get("url", "")
                    })
            except Exception:
                # If news fails, try general text
                text_items = list(ddgs.text(query, max_results=max_results))
                for t in text_items:
                    results.append({
                        "title": t.get("title", ""),
                        "source": "Web Search",
                        "snippet": t.get("body", "")[:350],
                        "pubDate": "Live Web",
                        "link": t.get("href", "")
                    })
        return results
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

def fetch_realtime_knowledge(query: str, category: str = "general", lang: str = "en") -> list:
    """
    Unified Cascading Real-Time Knowledge Engine:
    - Weather connector for weather questions
    - Concurrent Google News RSS + DuckDuckGo + Wikipedia
    - Deep web page excerpt extraction on top URLs
    """
    if category == "weather" or any(w in query.lower() for w in ["weather", "temperature", "వాతావరణం"]):
        weather_res = fetch_weather_direct(query)
        if weather_res:
            return weather_res

    combined = []
    
    # 1. Google News RSS (Fastest & most up-to-date)
    gnews = fetch_google_news_rss(query, lang=lang)
    if gnews:
        combined.extend(gnews)

    # 2. DuckDuckGo (News / Text) if we need more depth
    if len(combined) < 3:
        ddg = fetch_duckduckgo_news_or_text(query)
        if ddg:
            combined.extend(ddg)

    # 3. Wikipedia API fallback for entities/topics
    if len(combined) < 2:
        wiki = fetch_wikipedia_search(query)
        if wiki:
            combined.extend(wiki)

    if not combined:
        return []

    # 4. Deep Page Extraction on the top 1-2 articles for richer context
    for item in combined[:2]:
        link = item.get("link", "")
        if link and link.startswith("http") and "google.com" not in link:
            deep_text = fetch_deep_snippet(link, max_chars=700)
            if deep_text and len(deep_text) > 100:
                item["snippet"] = deep_text

    return combined

# Backwards compatibility wrappers
def fetch_live_news(query='sports', lang='en'):
    return fetch_realtime_knowledge(query, category='news', lang=lang)

def fetch_web_search(query, num_results=10):
    return fetch_realtime_knowledge(query, category='web', lang='en')

def fetch_current_anime(msg: str):
    return fetch_realtime_knowledge(f"latest anime news release {msg}", category='anime', lang='en')

def call_ai_chat_stream(prompt_or_messages, system_instruction, history=None):
    from backend.main import groq_client
    if not groq_client:
        yield "AI services are currently offline. Please check API keys."
        return

    messages = [{"role": "system", "content": system_instruction}]
    if history:
        for h in history[-6:]:
            content = h.get("content", "")
            if content and not any(phrase in content.lower() for phrase in
                                   ["text-based mode", "cannot directly access",
                                    "do not have the capability", "unable to view", "groq api error"]):
                messages.append({"role": h.get("role", "user"), "content": content})

    messages.append({"role": "user", "content": prompt_or_messages if isinstance(prompt_or_messages, str) else str(prompt_or_messages)})

    candidate_models = ["qwen/qwen3.8-27b", "groq/compound-mini", "openai/gpt-oss-20b"]
    for model_name in candidate_models:
        try:
            res = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=600,
                temperature=0.6,
                stream=True
            )

            streamed_any = False
            for chunk in res:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    streamed_any = True
                    yield chunk.choices[0].delta.content
            
            if streamed_any:
                return
        except Exception as groq_err:
            print(f"Groq stream error with {model_name}: {groq_err}")
            continue

    yield "I apologize, but I am having trouble connecting right now. Please try again in a moment."

@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    start_ms = int(time.time() * 1000)
    try:
        user = get_current_user(request)
        system = req.system_prompt if req.system_prompt else DEFAULT_PROMPT
        system += f"\n\n{get_dynamic_temporal_context()}\n"
        system += "\n\nCRITICAL INSTRUCTION: If you are responding in Telugu or any other regional language, you MUST NOT include any Chinese, Japanese, or unrelated languages in your response. Keep your output strictly to the requested language (and English if necessary for technical terms)."
        
        
        if req.tone == "friendly":
            system += "\n\nTONE INSTRUCTION: You MUST speak in a very friendly, warm, and casual tone. Use approachable language, be empathetic, and act like a good friend."
        elif req.tone == "professional":
            system += "\n\nTONE INSTRUCTION: You MUST speak in a strictly professional, formal, and objective tone. Be highly concise, polite, and avoid casual language."
        elif req.tone == "normal":
            system += "\n\nTONE INSTRUCTION: Speak in your normal, balanced, factual tone. Be helpful and clear without being overly emotional or rigidly formal."
        else:
            system += "\n\nDYNAMIC TONE MATCHING: Analyze the user's tone (e.g., friendly, professional, casual, serious, use of slang, short vs long sentences). You MUST perfectly mirror their behavior and emotional tone. Act like a human peer to the user. Do not explicitly state that you are mirroring them. Maintain your core identity as Mikey."

        system += "\n\nSAFETY AND BEHAVIOR INSTRUCTION: Always maintain absolute respect for the user. Do not misbehave, use inappropriate language, or be rude under any circumstances, even if the user's tone is aggressive. Maintain a helpful and safe demeanor."
        if req.persona == "technical":
            system += "\n\nOperating Mode: Technical Specialist. Provide detailed, analytical explanations, include code snippets or structural breakdowns where appropriate."
        elif req.persona == "creative":
            system += "\n\nOperating Mode: Creative Strategist. Offer innovative proposals, multi-angle ideas, and engaging options."
        else:
            system += "\n\nOperating Mode: Executive Assistant. Be concise, direct, strategic, and focus on high-impact insights."

        if user:
            docs = load_documents(user["id"])
            if docs:
                docs_context = build_context_text(docs, max_chars=2000)
                system += f"\n\nHere are some documents the user has uploaded for context:\n{docs_context}\nUse this context to directly answer the user's specific questions. Do NOT explain or summarize all the papers in the document unless the user explicitly asks for a full summary. Just answer what they specifically asked about, using simple, easy-to-understand language like ChatGPT or Claude."

        # ── UNIVERSAL INTENT ROUTER & PIPELINE INJECTION ──
        req_id = f"req_{int(time.time()*1000)}"
        
        intent_info = universal_intent_router(req.message)
        intent = intent_info["intent"]
        lang = intent_info["language"]
        req_live = intent_info["requires_live_data"]
        
        print(f"\n[DEBUG] BACKEND CHAT REQUEST")
        print(f"[DEBUG] REQUEST ID: {req_id}")
        print(f"[DEBUG] MESSAGE: {req.message}")
        print(f"[DEBUG] PATH: /chat")
        print(f"[DEBUG] INTENT DETECTION: {intent_info}")
        
        if req_live:
            search_query = intent_info.get("query", req.message)
            category = intent_info.get("category", "general")
            print(f"[DEBUG] LIVE RETRIEVAL: {search_query} ({category})")
            live_data = fetch_realtime_knowledge(search_query, category=category, lang=lang)
            if not live_data:
                live_data = fetch_realtime_knowledge(req.message, category="general", lang=lang)
                
            if live_data:
                print(f"[DEBUG] LIVE ARTICLES RETRIEVED: {len(live_data)}")
                context_str = "\n".join([f"- Title: {n['title']}\n  Source: {n['source']} ({n.get('pubDate', '')})\n  Snippet: {n.get('snippet', '')}\n  URL: {n['link']}" for n in live_data])
                system += (
                    "\n\nCRITICAL INSTRUCTION FOR CURRENT REQUEST: "
                    "The user is asking for CURRENT/LIVE information. Real-time web intelligence has been retrieved below. "
                    "DO NOT say you don't have real-time access or mention knowledge cutoffs. Summarize the retrieved data below into concise, authoritative points as of 2026. "
                    "You MUST include the source as a strict markdown link at the end of each point: `[Source Name](URL)`.\n\n"
                    "=== RETRIEVED REAL-TIME WEB DATA ===\n"
                    f"{context_str}\n"
                    "=====================================\n\n"
                )

        else:
            if intent == "ANIME_RECOMMENDATION":
                system += "\n\nThe user is asking for an Anime recommendation. Provide a standout anime, a concise summary, and a 'Why watch' section with bullet points."
            elif intent == "STUDY":
                system += "\n\nThe user is asking for study strategies. Provide practical, structured answers like Active Recall, Spaced Repetition, and Pomodoro. Be highly organized and encouraging."
            elif intent == "HEALTH":
                system += "\n\nThe user is asking for health/lifestyle advice. IMPORTANT: Do not present medical diagnosis as certainty. Provide general information, acknowledge uncertainty, and recommend professional medical care when appropriate."

        print(f"[DEBUG] LLM SUMMARY: executing...")

        reply = call_ai_chat(req.message, system_instruction=system, history=req.history, image_url=req.image_url, is_doc_task=False)

        if user and req.thread_id:
            save_chat_message(user["id"], req.thread_id, "user", req.message, req.image_url)
            save_chat_message(user["id"], req.thread_id, "assistant", reply)
            log_event(user["id"], "chat_request", req.message[:1024] if req.message else "image")
            
        log_api_usage(user["id"] if user else None, "/chat", int(time.time() * 1000) - start_ms, True)
        
        print(f"[DEBUG] RESPONSE CREATED for {req_id}")
        return {"reply": reply, "request_id": req_id}
    except Exception as e:
        log_api_usage(None, "/chat", int(time.time() * 1000) - start_ms, False)
        print(f"AI ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream_chat")
async def stream_chat(req: ChatRequest, request: Request):
    user = get_current_user(request)
    system = req.system_prompt if req.system_prompt else DEFAULT_PROMPT
    system += f"\n\n{get_dynamic_temporal_context()}\n"
    system += "\n\nCRITICAL INSTRUCTION: If you are responding in Telugu or any other regional language, you MUST NOT include any Chinese, Japanese, or unrelated languages in your response. Keep your output strictly to the requested language (and English if necessary for technical terms)."
    
    system += "\n\nSAFETY AND BEHAVIOR INSTRUCTION: Always maintain absolute respect for the user. Do not misbehave, use inappropriate language, or be rude under any circumstances, even if the user's tone is aggressive. Maintain a helpful and safe demeanor."
    
    if req.tone == "friendly":
        system += "\n\nTONE INSTRUCTION: You MUST speak in a very friendly, warm, and casual tone. Use approachable language, be empathetic, and act like a good friend."
    elif req.tone == "professional":
        system += "\n\nTONE INSTRUCTION: You MUST speak in a strictly professional, formal, and objective tone. Be highly concise, polite, and avoid casual language."
    elif req.tone == "normal":
        system += "\n\nTONE INSTRUCTION: Speak in your normal, balanced, factual tone. Be helpful and clear without being overly emotional or rigidly formal."
    else:
        system += "\n\nDYNAMIC TONE MATCHING: Analyze the user's tone (e.g., friendly, professional, casual, serious, use of slang, short vs long sentences). You MUST perfectly mirror their behavior and emotional tone. Act like a human peer to the user. Do not explicitly state that you are mirroring them. Maintain your core identity as Mikey."
    
    if req.persona == "technical":
        system += "\n\nOperating Mode: Technical Specialist. Provide detailed, analytical explanations, include code snippets or structural breakdowns where appropriate."
    elif req.persona == "creative":
        system += "\n\nOperating Mode: Creative Strategist. Offer innovative proposals, multi-angle ideas, and engaging options."
    else:
        system += "\n\nOperating Mode: Executive Assistant. Be concise, direct, strategic, and focus on high-impact insights."

    if user:
        docs = load_documents(user["id"])
        if docs:
            docs_context = build_context_text(docs, max_chars=2000)
            system += f"\n\nHere are some documents the user has uploaded for context:\n{docs_context}\nUse this context to directly answer the user's specific questions. Do NOT explain or summarize all the papers in the document unless the user explicitly asks for a full summary. Just answer what they specifically asked about, using simple, easy-to-understand language like ChatGPT or Claude."

    req_id = f"req_{int(time.time()*1000)}"
    intent_info = universal_intent_router(req.message)
    intent = intent_info["intent"]
    lang = intent_info["language"]
    req_live = intent_info["requires_live_data"]
    
    live_data = None
    if req_live:
        search_query = intent_info.get("query", req.message)
        category = intent_info.get("category", "general")
        print(f"[DEBUG] STREAM LIVE SEARCH: {search_query} ({category})")
        live_data = await asyncio.to_thread(fetch_realtime_knowledge, search_query, category, lang)
        if not live_data:
            live_data = await asyncio.to_thread(fetch_realtime_knowledge, req.message, "general", lang)
            
        if live_data:
            print(f"[DEBUG] STREAM LIVE DATA ITEMS: {len(live_data)}")
            context_str = "\n".join([f"- Title: {n['title']}\n  Source: {n['source']} ({n.get('pubDate', '')})\n  Snippet: {n.get('snippet', '')}" for n in live_data])
            system += (
                f"\n\nCRITICAL REAL-TIME GROUNDING (Operating Year 2026):\n"
                f"The user is asking for current, live, or real-time information. Real-time web intelligence has been retrieved below.\n"
                f"- Synthesize the retrieved data into a concise, direct, and authoritative response.\n"
                f"- NEVER state that you have a knowledge cutoff, lack real-time access, or cannot browse the web.\n"
                f"- Do NOT output raw web URLs in the text body. The system will automatically attach verified source links at the end.\n\n"
                f"=== RETRIEVED REAL-TIME WEB DATA ===\n"
                f"{context_str}\n"
                f"=====================================\n\n"
                f"Format your response clearly. If the user asked in Telugu, translate the summary and respond entirely in Telugu."
            )

    if not req_live:
        if intent == "ANIME_RECOMMENDATION":
            system += "\n\nThe user is asking for an Anime recommendation. Provide a standout anime, a concise summary, and a 'Why watch' section with bullet points."
        elif intent == "STUDY":
            system += "\n\nThe user is asking for study strategies. Provide practical, structured answers like Active Recall, Spaced Repetition, and Pomodoro. Be highly organized and encouraging."
        elif intent == "HEALTH":
            system += "\n\nThe user is asking for health/lifestyle advice. IMPORTANT: Do not present medical diagnosis as certainty. Provide general information, acknowledge uncertainty, and recommend professional medical care when appropriate."

    async def event_generator():
        full_reply = ""
        try:
            # Fallback to non-streaming multimodal if image is attached
            if req.image_url:
                full_reply = await asyncio.to_thread(
                    call_ai_chat,
                    req.message,
                    system,
                    req.history,
                    req.image_url,
                    False
                )
                yield full_reply
            else:
                for chunk in call_ai_chat_stream(req.message, system, req.history):
                    full_reply += chunk
                    yield chunk
                    
            # Append programmatic sources for live data
            if getattr(req, 'live_data_fetched', False) or (req_live and live_data):
                sources_text = "\n\n**Sources:**\n"
                for n in live_data[:4]:
                    if n.get('link'):
                        raw_title = n.get('title') or n.get('source') or 'Source'
                        short_title = raw_title.split(' - ')[0].split(' | ')[0][:50]
                        sources_text += f"- [{short_title}]({n['link']})\n"
                full_reply += sources_text
                yield sources_text
        except Exception as stream_err:
            print(f"[STREAM ERROR] {stream_err}")
            if not full_reply:
                yield "I apologize, but I encountered an issue generating a response. Please try again."

        # After stream finishes, save to DB safely without interrupting the response
        try:
            if user and req.thread_id and full_reply:
                save_chat_message(user["id"], req.thread_id, "user", req.message, req.image_url)
                save_chat_message(user["id"], req.thread_id, "assistant", full_reply)
                log_event(user["id"], "chat_request_stream", req.message[:1024] if req.message else "image")
        except Exception as db_err:
            print(f"[STREAM DB SAVE WARNING] {db_err}")

    return StreamingResponse(
        event_generator(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.get("/tts")
async def tts(text: str, lang: str = "en", rate: Optional[str] = None):
    try:
        raw_text = (text or "").strip()
        clean_text = strip_markdown_for_tts(raw_text)
        if not clean_text or not re.search(r'[\w\u0C00-\u0C7F]', clean_text):
            clean_text = "OK"

        # Format rate (e.g., "+0%", "+15%", "+20%")
        tts_rate = "+0%"
        if rate:
            r_str = rate.strip()
            if r_str.startswith("+") or r_str.startswith("-"):
                tts_rate = r_str
            else:
                try:
                    val = float(r_str)
                    pct = int(round((val - 1.0) * 100))
                    tts_rate = f"{'+' if pct >= 0 else ''}{pct}%"
                except Exception:
                    tts_rate = "+0%"

        is_te = lang.lower().startswith("te")
        voice = "te-IN-MohanNeural" if is_te else "en-US-GuyNeural"
        cache_key = hashlib.md5(f"{clean_text}:{voice}:{tts_rate}".encode("utf-8")).hexdigest()

        # Check in-memory cache
        cached_bytes = _get_tts_cache(cache_key)
        if cached_bytes:
            return Response(content=cached_bytes, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})

        audio_bytes = None

        # Method 1: Edge-TTS with timeout
        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean_text, voice, rate=tts_rate)
            audio_io = BytesIO()

            async def _collect_edge():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_io.write(chunk["data"])

            await asyncio.wait_for(_collect_edge(), timeout=8.0)
            audio_bytes = audio_io.getvalue()
        except Exception as edge_err:
            print(f"Edge-TTS failed/timed out for '{clean_text[:25]}...': {edge_err}. Attempting gTTS fallback...")

        # Method 2: gTTS Fallback
        if not audio_bytes and gTTS:
            try:
                gtts_lang = "te" if is_te else "en"
                tts_obj = gTTS(text=clean_text, lang=gtts_lang, slow=False)
                audio_io = BytesIO()
                tts_obj.write_to_fp(audio_io)
                audio_bytes = audio_io.getvalue()
            except Exception as gtts_err:
                print(f"gTTS fallback failed: {gtts_err}")

        if audio_bytes:
            _set_tts_cache(cache_key, audio_bytes)
            return Response(content=audio_bytes, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})

        raise HTTPException(status_code=500, detail="Voice synthesis failed across all providers")
    except HTTPException:
        raise
    except Exception as e:
        print("TTS Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), lang: Optional[str] = "en"):
    from backend.main import groq_client
    if not groq_client:
        raise HTTPException(status_code=503, detail="Groq transcription client unavailable")
    try:
        audio_content = await file.read()
        if not audio_content:
            raise HTTPException(status_code=400, detail="Empty audio received")
        
        file_tuple = (file.filename or "recording.webm", audio_content, file.content_type or "audio/webm")
        whisper_lang = "te" if (lang and lang.lower().startswith("te")) else "en"

        transcription = groq_client.audio.transcriptions.create(
            file=file_tuple,
            model="whisper-large-v3-turbo",
            response_format="json",
            language=whisper_lang
        )
        return {"text": transcription.text.strip()}
    except HTTPException:
        raise
    except Exception as e:
        print("Audio transcription error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/weather")
async def weather(req: WeatherRequest):
    try:
        if not WEATHER_API_KEY:
            raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured")
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={req.city}&appid={WEATHER_API_KEY}&units=metric"
        )

        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="City not found")
        d = r.json()
        return {
            "city": d["name"],
            "country": d["sys"]["country"],
            "temp": round(d["main"]["temp"]),
            "feels_like": round(d["main"]["feels_like"]),
            "humidity": d["main"]["humidity"],
            "description": d["weather"][0]["description"].title(),
            "icon": d["weather"][0]["icon"],
            "wind": round(d["wind"]["speed"] * 3.6),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/open-url")
def open_url_endpoint(req: OpenUrlRequest):
    import webbrowser
    try:
        webbrowser.open(req.url)
        return {"ok": True, "message": f"Opened {req.url} on host browser"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    avatars_dir = os.path.join(frontend_dir, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    
    file_path = os.path.join(avatars_dir, f"{user['username']}.jpg")
    
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
        
    return {"message": "Avatar uploaded successfully", "avatarUrl": f"/static/avatars/{user['username']}.jpg?v={int(time.time())}"}

# ── Serve static files ────────────────────────────────────────────────────────
