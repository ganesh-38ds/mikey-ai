# 🧠 Mikey - Full-Stack AI Assistant

## 📌 Project Overview
Mikey is a dynamic, full-stack AI web application designed to be your ultimate friendly chat companion, featuring continuous voice mode, live internet access, and autonomous tone-matching in a modern dark-themed UI.

## ❓ Problem Statement
Traditional AI chatbots often feel robotic, require constant manual typing, and lack real-time awareness of the outside world. Mikey solves this by providing a continuous, hands-free voice interface, emotionally intelligent tone-matching, and the ability to pull in live web data—creating a companion that feels alive and contextually aware.

## 🎬 Demo
*(Add a screenshot, GIF, or link to a video demonstrating Mikey's voice mode and UI here)*

## 🎯 Objectives
* Deliver a highly friendly and natural conversational chat experience.
* Provide a hands-free, continuous "Live Talk Mode" for fluid voice-to-voice interaction.
* Intercept queries securely to fetch live web searches and news headlines.
* Enhance visual intelligence through cutting-edge multimodal image analysis.

## 📈 Key Features
* **Live Voice Mode:** An endless conversational loop that pauses listening while the AI speaks.
* **Dynamic Tone Matching:** AI passively mirrors your emotional state for a highly empathetic connection.
* **Smart Live Web Hooking:** Automatically decrypts and streams live news feeds directly into the chat.
* **Multimodal Vision:** Seamlessly analyze uploaded images through state-of-the-art vision models.
* **Admin Dashboard:** Hidden administrative panel to track platform engagement and user stats.

## 🛠️ Tools & Technologies Used
* **Python & JavaScript:** Core programming languages powering the backend and interactive frontend.
* **FastAPI (Uvicorn):** High-performance backend framework for handling asynchronous AI streaming.
* **Groq API & Gemini API:** Ultra-low latency LLMs for text and advanced vision models for images.
* **Web Speech API & Edge-TTS:** Browser-native speech recognition and high-quality voice synthesis.
* **googlenewsdecoder & duckduckgo_search:** Secure RSS decryption and web scraping for live real-time data.
* **HTML5 & CSS3:** Custom Dark Mode styling for a sleek, modern UI.

## 🗄️ Database Architecture (SQLite3)
* **Users & Sessions:** Secure authentication and active login tracking.
* **Chat Threads & Messages:** Isolated conversation histories and multimodal image tracking.
* **Knowledge Documents:** Storage for personal text files to build a contextual knowledge base.
* **Analytics & API Usage:** Logs backend interactions for the hidden Admin Dashboard.
* **User Preferences:** Saves individual user settings like language or persona choices.

## 🏆 Results & Impact
* Achieved ultra-low latency conversational responses using the Groq API.
* Successfully eliminated audio-feedback loops during continuous voice interaction.
* Created a seamless integration between local application logic and live web data parsing.

## 🚀 How to Run Locally
1. **Clone the repository:** `git clone https://github.com/ganesh-38ds/mikey-ai.git`
2. **Setup Environment:** Create a `.env` file with `GROQ_API_KEY` and `GEMINI_API_KEY`.
3. **Install dependencies:** `pip install -r requirements.txt`
4. **Run the server:** `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`
5. **View the app:** Open `http://127.0.0.1:8000` in your browser.

## 💻 Developer
**Gudla Ganesh**
* **Email:** [ganeshgudla944@gmail.com](mailto:ganeshgudla944@gmail.com)
* **GitHub:** [https://github.com/ganesh-38ds](https://github.com/ganesh-38ds)
* **LinkedIn:** [https://www.linkedin.com/in/gudla-ganesh-ab3816407](https://www.linkedin.com/in/gudla-ganesh-ab3816407)
* **Role:** Full-Stack Developer & AI Integrator
