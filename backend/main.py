import sys

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
import httpx
import os
import hashlib
import sqlite3
import uuid
import time
from datetime import datetime
from io import BytesIO
import base64

# Use new google-genai SDK if available, fall back to legacy
try:
    from google import genai as genai_new
    from google.genai import types as genai_types
    _use_new_genai = True
except ImportError:
    genai_new = None
    genai_types = None
    _use_new_genai = False

try:
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai_legacy
except Exception as e:
    print(f"[WARNING] Could not import google.generativeai: {type(e).__name__}: {str(e)[:100]}")
    genai_legacy = None

from dotenv import load_dotenv
from typing import Optional

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

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

try:
    from groq import Groq
except ImportError:
    Groq = None

# ── Load keys from .env file ──────────────────────────────────────────────────
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
from backend.database import DB_PATH
DATABASE_URL = os.getenv("DATABASE_URL")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mikey")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Mikey",
        "timestamp": datetime.utcnow().isoformat()
    }

def get_groq_client():
    return groq_client

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

groq_client = Groq(api_key=GROQ_API_KEY) if (Groq and GROQ_API_KEY) else None

# ── Gemini setup ──────────────────────────────────────────────────────────────
gemini_client = None
gemini_enabled = False

def _init_gemini(api_key: str) -> bool:
    """Initialize Gemini with the given API key. Returns True if successful."""
    global gemini_client, gemini_enabled
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return False
    try:
        if _use_new_genai and genai_new:
            gemini_client = genai_new.Client(api_key=api_key)
            # Quick connectivity test
            gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents="ping"
            )
        elif genai_legacy:
            genai_legacy.configure(api_key=api_key)
            genai_legacy.GenerativeModel("gemini-1.5-flash").generate_content("ping")
            gemini_client = genai_legacy
        else:
            return False
        gemini_enabled = True
        return True
    except Exception as e:
        print(f"Gemini init failed: {e}")
        gemini_enabled = False
        return False

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    _init_gemini(GEMINI_API_KEY)

# ── Default system prompt (fallback) ─────────────────────────────────────────
DEFAULT_PROMPT = """You are Mikey — the central command intelligence for the Mikey project and an advanced executive AI assistant operating in 2026.

## PROJECT CONTEXT
You are embedded inside the Mikey dashboard — a full-stack AI assistant web application built with:
- Backend: FastAPI (Python), SQLite, Groq LLM API, Google Gemini API (optional), gTTS TTS
- Frontend: Vanilla HTML/CSS/JS (single file: static/index.html)
- Key endpoints: /chat, /upload-chat-image, /upload, /ask-knowledge, /analyze-documents, /tts, /weather, /reminders, /api/threads, /api/save-gemini-key
- Styling: CSS custom properties, glassmorphism, dark theme, Outfit/Inter fonts, cyan/violet/emerald theme system

## COMMAND INTERFACE RULES
When a user gives a project command (e.g. "add X", "fix Y", "change Z", "hide W"):

ALWAYS respond in this exact format:

**Understood. I will [brief action].**

**Implementation Plan:**
• [specific change 1]
• [specific change 2]
• [specific change 3 if needed]

**Files affected:** [list the file(s) that will be modified]

**Awaiting confirmation to proceed.** _(Reply "confirm" or "yes" to execute, or modify the plan.)_

---

  When confirming after implementation (system will inject a ✅ SYSTEM message), acknowledge it naturally.
  
  ## EXPLAINING CONCEPTS, Q&A, & SUBJECTS
  When a user asks to understand a concept, asks Q&A questions, or explores a topic, you MUST structure your response as plain text lists. 
  DO NOT USE TABLES. Tables are strictly forbidden for concepts, summaries, and Q&A.
  Format your response exactly like this:
  
  1: [Topic or Question] 🏗️
  [Short, simple explanation in easily understandable language.]
  [Code examples if any, inside normal ``` blocks]
  _________________

  2: [Next Topic or Question] 🚀
  [Explanation...]
  _________________

  Always use a colon `:` after the number. Always separate items with a literal line `_________________`. NEVER put code in a table.

  ## GENERAL ASSISTANT RULES
  - Current year is 2026. Treat it as present.
  - You have ACTIVE real-time web search and live grounding capabilities. Never claim you have a knowledge cutoff date, lack real-time awareness, or cannot browse the web.
  - When real-time data or live search excerpts are injected into context, synthesize them into direct, authoritative, and present-day facts.
  - You ARE connected to a microphone transcription pipeline. If the user mentions voice, speaking, or listening, DO NOT say you lack audio capabilities. Acknowledge that you are receiving their transcribed speech.
  - NEVER use tables for Q&A or concept summaries. Always use the `1: [Topic]` format with `___` separators.
  - For non-project questions, answer normally as an executive AI assistant.
  - Be concise, professional, and precise.
  - For project commands, ALWAYS show the structured plan above — never skip it."""


from fastapi.staticfiles import StaticFiles
from fastapi.staticfiles import StaticFiles
from backend.routes import router
app.include_router(router)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")), name="static")
