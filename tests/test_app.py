import os
import shutil
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))
import main
import backend.database as database


class MikeyAppTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_mikey.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db
        main.DB_PATH = self.test_db
        database.init_db()
        self.client = TestClient(main.app)

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        main.DB_PATH = self.orig_db_path
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_auth_and_preferences_lifecycle(self):
        # 1. Signup
        signup = self.client.post('/signup', json={'username': 'testuser', 'password': 'password123'})
        self.assertEqual(signup.status_code, 200)
        self.assertIn('session_id', signup.cookies)

        # 2. Get Current User Me
        me = self.client.get('/me')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['username'], 'testuser')

        # 3. Update Preferences
        prefs = self.client.post('/preferences', json={'lang': 'te', 'tts_enabled': False, 'voice_input_enabled': True})
        self.assertEqual(prefs.status_code, 200)
        self.assertEqual(prefs.json()['lang'], 'te')
        self.assertFalse(prefs.json()['tts_enabled'])

        # 4. History
        history = self.client.get('/history')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()['conversations'], [])

        # 5. Logout
        logout = self.client.post('/logout')
        self.assertEqual(logout.status_code, 200)

        # 6. Me after logout should be 401
        me_after = self.client.get('/me')
        self.assertEqual(me_after.status_code, 401)

        # 7. Login again
        login = self.client.post('/login', json={'username': 'testuser', 'password': 'password123'})
        self.assertEqual(login.status_code, 200)

    @patch('backend.routes.call_ai_chat')
    def test_chat_and_threads_api(self, mock_ai):
        mock_ai.return_value = "Hello! I am Mikey executive assistant."
        
        # Signup user
        self.client.post('/signup', json={'username': 'threaduser', 'password': 'password123'})

        # Create thread
        t_create = self.client.post('/api/threads', json={'id': 'thread-001', 'title': 'Test Thread'})
        self.assertEqual(t_create.status_code, 200)

        # List threads
        t_list = self.client.get('/api/threads')
        self.assertEqual(t_list.status_code, 200)
        self.assertEqual(len(t_list.json()['threads']), 1)
        self.assertEqual(t_list.json()['threads'][0]['id'], 'thread-001')

        # Send chat message with thread_id & persona
        chat_res = self.client.post('/chat', json={
            'thread_id': 'thread-001',
            'message': 'Hello AI',
            'history': [],
            'lang': 'en',
            'persona': 'technical'
        })
        self.assertEqual(chat_res.status_code, 200)
        self.assertEqual(chat_res.json()['reply'], "Hello! I am Mikey executive assistant.")

        # Get thread messages
        msg_res = self.client.get('/api/threads/thread-001')
        self.assertEqual(msg_res.status_code, 200)
        messages = msg_res.json()['messages']
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['content'], 'Hello AI')
        self.assertEqual(messages[1]['content'], "Hello! I am Mikey executive assistant.")

        # Update thread title
        up_res = self.client.put('/api/threads/thread-001', json={'title': 'Updated Title'})
        self.assertEqual(up_res.status_code, 200)

        # Delete thread
        del_res = self.client.delete('/api/threads/thread-001')
        self.assertEqual(del_res.status_code, 200)

        # Confirm deleted
        t_list_after = self.client.get('/api/threads')
        self.assertEqual(len(t_list_after.json()['threads']), 0)

    @patch('backend.routes.call_ai_chat')
    def test_document_upload_list_and_delete(self, mock_ai):
        mock_ai.return_value = "Analysis of document context completed."
        self.client.post('/signup', json={'username': 'docuser', 'password': 'password123'})

        # Upload TXT file
        test_content = b"Mikey is an executive AI platform built with FastAPI in 2026."
        files = {"file": ("mikey_info.txt", test_content, "text/plain")}
        up_res = self.client.post('/upload', files=files)
        self.assertEqual(up_res.status_code, 200)
        self.assertEqual(up_res.json()['filename'], 'mikey_info.txt')

        # List documents
        doc_list = self.client.get('/documents')
        self.assertEqual(doc_list.status_code, 200)
        docs = doc_list.json()['documents']
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['filename'], 'mikey_info.txt')

        # Ask knowledge
        ask_res = self.client.post('/ask-knowledge', data={'question': 'What is Mikey?'})
        self.assertEqual(ask_res.status_code, 200)
        self.assertIn('answer', ask_res.json())

        # Analyze documents
        an_res = self.client.post('/analyze-documents')
        self.assertEqual(an_res.status_code, 200)
        self.assertIn('analysis', an_res.json())

        # Delete document
        doc_id = docs[0]['id']
        del_doc = self.client.delete(f'/documents/{doc_id}')
        self.assertEqual(del_doc.status_code, 200)

        # Verify empty list
        doc_list_after = self.client.get('/documents')
        self.assertEqual(len(doc_list_after.json()['documents']), 0)

    def test_reminders_and_analytics(self):
        self.client.post('/signup', json={'username': 'remuser', 'password': 'password123'})

        # Create reminder
        rem_res = self.client.post('/reminders', json={
            'title': 'Review Quarterly Budget',
            'scheduled_at': '2026-08-20 14:00',
            'description': 'Check Q3 numbers'
        })
        self.assertEqual(rem_res.status_code, 200)

        # List reminders
        get_rems = self.client.get('/reminders')
        self.assertEqual(get_rems.status_code, 200)
        rems = get_rems.json()['reminders']
        self.assertEqual(len(rems), 1)
        self.assertEqual(rems[0]['title'], 'Review Quarterly Budget')

        # Complete reminder
        comp_res = self.client.post(f"/reminders/{rems[0]['id']}/complete")
        self.assertEqual(comp_res.status_code, 200)

        # Log analytics event
        evt_res = self.client.post('/analytics/event', json={'event_type': 'test_event', 'metadata': 'meta_data'})
        self.assertEqual(evt_res.status_code, 200)

        # Admin stats & analytics
        stats = self.client.get('/admin/stats')
        self.assertEqual(stats.status_code, 200)
        self.assertGreaterEqual(stats.json()['user_count'], 1)
        self.assertEqual(stats.json()['reminder_count'], 1)

        an_list = self.client.get('/admin/analytics')
        self.assertEqual(an_list.status_code, 200)

    def test_tts_and_upload_chat_image(self):
        # TTS endpoint
        tts_res = self.client.get('/tts', params={'text': 'Hello **World**', 'lang': 'en'})
        self.assertEqual(tts_res.status_code, 200)
        self.assertEqual(tts_res.headers['content-type'], 'audio/mpeg')

        # Upload chat image endpoint
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        files = {"file": ("test.png", png_bytes, "image/png")}
        img_res = self.client.post('/upload-chat-image', files=files)
        self.assertEqual(img_res.status_code, 200)
        self.assertTrue(img_res.json()['url'].startswith('/uploads/'))

    def test_clear_all_history(self):
        self.client.post('/signup', json={'username': 'clearuser', 'password': 'password123'})
        self.client.post('/api/threads', json={'id': 'th-clear', 'title': 'Clear Me'})
        
        clear_res = self.client.delete('/api/clear-history')
        self.assertEqual(clear_res.status_code, 200)

        t_list = self.client.get('/api/threads')
        self.assertEqual(len(t_list.json()['threads']), 0)


if __name__ == '__main__':
    unittest.main()
