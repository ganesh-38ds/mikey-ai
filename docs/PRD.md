# Product Requirements Document (PRD) - Mikey AI Assistant

## 1. Product Overview
Mikey is a dynamic, full-stack AI web application designed to serve as an intelligent, conversational companion. It features continuous voice interaction, live internet access for real-time data retrieval, multimodal image analysis, and an emotionally adaptive text and voice chat interface within a sleek, dark-themed UI.

## 2. Target Audience
- Users seeking a hands-free, continuous voice-based AI assistant.
- Developers and power users needing quick access to live web searches, news, and weather.
- Individuals looking for a personalized, context-aware, and emotionally responsive conversational partner.

## 3. Core Features & Requirements

### 3.1 Live Conversational Chat
- **Requirement:** Secure and fast communication with LLMs (Groq & Gemini).
- **Details:** The system must support contextual, multi-turn conversations with history stored locally.

### 3.2 Continuous Voice Mode ("Live Talk")
- **Requirement:** Hands-free interaction loop.
- **Details:** The frontend should actively listen using the Web Speech API. It must pause listening while the AI response is synthesized and played (via Edge-TTS or Web Speech API fallback) to avoid feedback loops.

### 3.3 Dynamic Tone Matching
- **Requirement:** Emotionally intelligent responses.
- **Details:** The AI should passively analyze user sentiment and mirror emotional states to provide empathetic interactions.

### 3.4 Live Web Hooking & Real-Time Data
- **Requirement:** Access to real-time information.
- **Details:** The system must intercept specific queries (e.g., news, weather, searches) and use external APIs (OpenWeatherMap, duckduckgo_search, googlenewsdecoder) to retrieve and inject live data into the chat context.

### 3.5 Multimodal Vision Capabilities
- **Requirement:** Image analysis.
- **Details:** Users must be able to upload images for the AI to analyze and describe using state-of-the-art vision models (e.g., Gemini).

### 3.6 Data Persistence & Admin Dashboard
- **Requirement:** Local data management.
- **Details:** The application will use SQLite to manage User Sessions, Chat Threads, Knowledge Documents, and Analytics. A hidden admin dashboard will be available for tracking platform engagement.

## 4. Non-Functional Requirements
- **Performance:** Ultra-low latency responses using Groq API for text.
- **Security:** API keys must be securely loaded via `.env`. User sessions must be authenticated and isolated.
- **Usability:** A modern, responsive HTML5/CSS3 UI with a dark mode default for visual comfort.
- **Deployability:** The system must be easily executable via a local Uvicorn server or the provided `start.bat` script.

## 5. Success Metrics
- Average response latency under 1 second for text queries.
- Zero audio-feedback loops during Live Voice Mode.
- Successful resolution of real-time web search and weather queries.
