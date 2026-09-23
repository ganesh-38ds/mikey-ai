import requests
import json

BASE_URL = "http://localhost:8000"
session = requests.Session()

print("--- TESTING ALL ENDPOINTS ---")

# 1. Signup / Login
r = session.post(f"{BASE_URL}/signup", json={"username": "fulltestuser", "password": "password123"})
print(f"[1] Signup: {r.status_code} {r.text[:100]}")

r = session.post(f"{BASE_URL}/login", json={"username": "fulltestuser", "password": "password123"})
print(f"[2] Login: {r.status_code} {r.text[:100]}")

# 2. User Info & Prefs
r = session.get(f"{BASE_URL}/me")
print(f"[3] /me: {r.status_code} {r.text[:100]}")

r = session.post(f"{BASE_URL}/preferences", json={"lang": "en", "tts_enabled": True, "voice_input_enabled": True})
print(f"[4] /preferences: {r.status_code} {r.text[:100]}")

# 3. Document Upload
with open("test_doc.txt", "w", encoding="utf-8") as f:
    f.write("Mikey is an executive AI assistant created in 2026. It features voice input, text-to-speech, weather data, document analysis, and chat memory.")

files = {"file": ("test_doc.txt", open("test_doc.txt", "rb"), "text/plain")}
r = session.post(f"{BASE_URL}/upload", files=files)
print(f"[5] /upload: {r.status_code} {r.text[:100]}")

# 4. Ask Knowledge
r = session.post(f"{BASE_URL}/ask-knowledge", data={"question": "What is Mikey?"})
print(f"[6] /ask-knowledge: {r.status_code} {r.text[:200]}")

# 5. Analyze Documents
r = session.post(f"{BASE_URL}/analyze-documents")
print(f"[7] /analyze-documents: {r.status_code} {r.text[:200]}")

# 6. Chat (Text)
r = session.post(f"{BASE_URL}/chat", json={"message": "Hello, who are you?", "history": [], "lang": "en"})
print(f"[8] /chat text: {r.status_code} {r.text[:200]}")

# 7. Chat Image Upload & Image Chat
png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
with open("test_img.png", "wb") as f:
    f.write(png_bytes)
with open("test_img.png", "rb") as f:
    r_img = session.post(f"{BASE_URL}/upload-chat-image", files={"file": f})
print(f"[9] /upload-chat-image: {r_img.status_code} {r_img.text[:100]}")
if r_img.status_code == 200:
    img_url = r_img.json().get("url")
    r_chat_img = session.post(f"{BASE_URL}/chat", json={"message": "Describe image", "image_url": img_url, "history": [], "lang": "en"})
    print(f"[10] /chat image: {r_chat_img.status_code} {r_chat_img.text[:200].encode('ascii', 'ignore').decode('ascii')}")

# 8. Weather
r = session.post(f"{BASE_URL}/weather", json={"city": "London"})
print(f"[11] /weather: {r.status_code} {r.text[:200]}")

# 9. TTS
r = session.get(f"{BASE_URL}/tts", params={"text": "Hello World", "lang": "en"})
print(f"[12] /tts: {r.status_code} Content-Type: {r.headers.get('content-type')}")

# 10. Reminders
r = session.post(f"{BASE_URL}/reminders", json={"title": "Test Directive", "scheduled_at": "2026-08-16 10:00", "description": "Test"})
print(f"[13] /reminders POST: {r.status_code} {r.text}")

r = session.get(f"{BASE_URL}/reminders")
print(f"[14] /reminders GET: {r.status_code} {r.text[:200]}")

# 11. Threads API
r = session.post(f"{BASE_URL}/api/threads", json={"id": "thread-123", "title": "Test Thread"})
print(f"[15] /api/threads POST: {r.status_code} {r.text}")

r = session.get(f"{BASE_URL}/api/threads")
print(f"[16] /api/threads GET: {r.status_code} {r.text[:200]}")

# 12. Clear History
r = session.delete(f"{BASE_URL}/api/clear-history")
print(f"[17] /api/clear-history: {r.status_code} {r.text}")

print("--- COMPLETED ALL TESTS ---")
