# System Design & UI/UX Approach

## 1. Design Philosophy
Mikey is designed to feel like a modern, sentient companion rather than a static tool. The design prioritizes minimal friction, fluid interactions, and visual comfort during extended usage.

## 2. User Interface (UI) Design
- **Dark Mode Default:** The interface uses a deep, dark color palette (e.g., `#121212` backgrounds with muted gray panels) to reduce eye strain and give a sleek, modern, "hacker/AI" aesthetic.
- **Responsive Layout:** The layout adapts to both desktop and mobile views, utilizing CSS Flexbox/Grid to ensure the chat window maximizes available space.
- **Chat Interface:** 
  - User messages align right (distinct accent color, e.g., soft blue).
  - AI responses align left (subtle dark gray background).
- **Interactive Elements:**
  - Micro-animations on buttons (hover states, click ripples).
  - A pulsing indicator or waveform visualization when the microphone is active (Live Voice Mode).
  - Clean card-based layouts for external data injections (e.g., weather widgets, news summaries).

## 3. User Experience (UX) Flow
- **Onboarding:** Zero-friction entry. The user opens the local URL and is immediately greeted by the chat interface without complex setup screens.
- **Voice Interaction:** The "Live Talk Mode" must feel conversational. The system uses Web Speech API to detect voice activity, automatically muting the microphone when the AI is speaking to prevent echo/feedback.
- **Multimodal Feedback:** When an image is uploaded, the UI provides a thumbnail preview before sending, and the AI acknowledges the image visually and textually.
- **Latency Masking:** While waiting for Groq/Gemini API responses, the UI displays a subtle typing indicator ("Mikey is thinking...") to provide immediate feedback that the request is processing.

## 4. Emotional Tone Matching Design
- The system prompt instructs the LLM to passively analyze the user's text/voice sentiment.
- If the user is excited, the AI responds with matching enthusiasm.
- If the user is frustrated, the AI adopts a calm, helpful, and concise tone.
- This creates a UX that feels highly personalized and empathetic.
