# Project Memory & Context

## 1. Project Identity
- **Name:** Mikey
- **Type:** Local AI Assistant Web Application
- **Author:** Gudla Ganesh

## 2. Key Architectural Decisions & Learnings
- **Why FastAPI?** Chosen for its high performance, native async support, and automatic documentation generation (Swagger UI), which makes API testing much faster.
- **Why Groq?** Selected as the primary text LLM provider over standard OpenAI due to its ultra-low latency inference (LPU technology), which is critical for making voice conversations feel real-time and natural.
- **Why SQLite?** Provides zero-configuration, local data persistence without requiring users to install and manage a separate database server (like PostgreSQL), fitting the lightweight nature of the app.
- **Voice Mode Challenges:** The biggest challenge in "Live Talk Mode" is preventing the microphone from picking up the AI's own audio output. The solution involves strictly toggling the listening state on the frontend based on the audio playback state.
- **Web Scraping Strategy:** Using APIs like `duckduckgo_search` and `googlenewsdecoder` allows the AI to ground its answers in real-time reality, bypassing the typical knowledge cutoff dates of base LLMs.

## 3. Current Context State
- The project has evolved from a simple script (`PROJECT_EXPLAINED.txt`) into a robust full-stack application with a database (`shadowcall.db`) and advanced integrations (Gemini Vision, Web Search).
- Documentation has been formalized to professional standards (PRD, ARCHITECTURE, DESIGN) to accurately reflect the current system complexity and aid in future onboarding or recruitment presentations.
