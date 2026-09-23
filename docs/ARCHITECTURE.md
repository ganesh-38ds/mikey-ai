# System Architecture - Mikey AI Assistant

## 1. High-Level Architecture Overview
Mikey follows a standard monolithic client-server architecture optimized for local execution and high-speed API brokering. The frontend communicates with a FastAPI backend, which in turn acts as a gateway to external AI and data APIs, persisting state in a local SQLite database.

## 2. Component Diagram

```mermaid
flowchart TD
    Client[Web Browser Client\n(HTML/CSS/JS, Web Speech API)]
    Backend[FastAPI Backend\n(Uvicorn Server)]
    DB[(SQLite3 Database)]
    
    GroqAPI[Groq API\n(LLM text engine)]
    GeminiAPI[Gemini API\n(Vision model)]
    ExternalAPIs[External Services\n(OpenWeatherMap, DuckDuckGo, News)]
    TTS[Edge-TTS / gTTS\n(Audio Synthesis)]

    Client <-->|REST / JSON| Backend
    Backend <-->|SQLAlchemy / SQL| DB
    Backend <-->|HTTP Requests| GroqAPI
    Backend <-->|HTTP Requests| GeminiAPI
    Backend <-->|HTTP Requests| ExternalAPIs
    Backend <-->|Local OS| TTS
```

## 3. Component Details

### 3.1 Frontend (Client)
- **Technologies:** Vanilla HTML5, CSS3, JavaScript.
- **Responsibilities:** 
  - Rendering the UI (chat window, weather cards, admin dashboard).
  - Capturing microphone input via Web Speech API.
  - Playing back audio responses.
  - Managing user interactions and state before sending to the backend.

### 3.2 Backend (FastAPI Server)
- **Technologies:** Python, FastAPI, Uvicorn, python-multipart.
- **Responsibilities:**
  - Routing API requests (`/chat`, `/weather`, `/tts`).
  - Handling business logic, intent recognition, and routing queries to the appropriate external service (LLM vs Web Search).
  - Processing image uploads.
  - Executing TTS generation and serving audio files.

### 3.3 Database Layer (SQLite3)
- **Technologies:** SQLite3 (Local file-based).
- **Responsibilities:**
  - Storing user credentials and active sessions.
  - Archiving chat threads and messages for context retrieval.
  - Storing knowledge base documents for Retrieval-Augmented Generation (RAG) capabilities.
  - Logging analytics for the admin dashboard.

### 3.4 External Integrations
- **Groq API:** Primary driver for conversational text generation (ultra-low latency).
- **Gemini API:** Utilized for advanced multimodal image processing.
- **OpenWeatherMap:** Live weather data provider.
- **DuckDuckGo/News:** Real-time web scraping and RSS decoding for live internet access.

## 4. Data Flow: Typical Chat Request
1. User types or speaks a prompt.
2. Frontend sends `POST /chat` with payload to Backend.
3. Backend retrieves conversation history from SQLite.
4. Backend evaluates if the prompt requires a web search.
   - If yes, fetches data from external APIs and appends to context.
5. Backend forwards the final prompt and context to Groq API.
6. Groq returns the generated response.
7. Backend saves the response to SQLite.
8. (Optional) Backend generates audio via TTS if Voice Mode is active.
9. Backend responds to Frontend with text (and audio payload).
10. Frontend updates the UI and plays audio.
