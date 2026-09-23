import os
import requests

filename = "dummy.txt"
with open(filename, "w", encoding="utf-8") as f:
    f.write("Mikey test document for automated upload verification.")

session = requests.Session()
r_login = session.post("http://localhost:8000/login", json={"username": "testuser123", "password": "password123"})
if r_login.status_code != 200:
    session.post("http://localhost:8000/signup", json={"username": "testuser123", "password": "password123"})
    r_login = session.post("http://localhost:8000/login", json={"username": "testuser123", "password": "password123"})

with open(filename, "rb") as fh:
    files = {"file": (filename, fh, "text/plain")}
    r_up = session.post("http://localhost:8000/upload", files=files)
    print("UPLOAD STATUS:", r_up.status_code)
    print("UPLOAD CONTENT:", r_up.text)

r_an = session.post("http://localhost:8000/analyze-documents")
print("ANALYZE STATUS:", r_an.status_code)
print("ANALYZE CONTENT:", r_an.text[:200])

if os.path.exists(filename):
    os.remove(filename)
