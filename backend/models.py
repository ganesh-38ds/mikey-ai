from pydantic import BaseModel, Field
from typing import Optional

# ── Pydantic models ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    image_url: Optional[str] = None
    message: str
    history: list = Field(default_factory=list)
    lang: Optional[str] = "en"
    system_prompt: Optional[str] = None   # frontend sends Telugu or English prompt
    persona: Optional[str] = "executive"
    tone: Optional[str] = "dynamic"

class WeatherRequest(BaseModel):
    city: str

class SignupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PreferencesRequest(BaseModel):
    lang: Optional[str] = None
    tts_enabled: Optional[bool] = None
    voice_input_enabled: Optional[bool] = None

class ReminderRequest(BaseModel):
    title: str
    scheduled_at: str
    description: Optional[str] = None

class AnalyticsEventRequest(BaseModel):
    event_type: str
    metadata: Optional[str] = None

class OpenUrlRequest(BaseModel):
    url: str

