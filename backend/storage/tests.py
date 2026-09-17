import io
import uuid
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import User, StoredFile

@override_settings(MEDIA_ROOT="/tmp/diplom-test-media")
class StorageApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User(
            login="tester",
            full_name="Test User",
            email="tester@example.com",
            storage_path=uuid.uuid4().hex,
        )
        self.user.set_password("Test123!")
        self.user.save()

    def login(self, user=None):
        user = user or self.user
        self.client.post("/api/auth/login/", {"login": user.login, "password": "Test123!" if user == self.user else "Admin123!"}, format="json")

    def test_register(self):
        response = self.client.post("/api/auth/register/", {
            "login": "newuser",
            "full_name": "New User",
            "email": "new@example.com",
            "password": "Secret1!"
        }, format="json")
        self.assertEqual(response.status_code, 201)

    def test_bad_password(self):
        response = self.client.post("/api/auth/register/", {
            "login": "newuser",
            "full_name": "New User",
            "email": "new@example.com",
            "password": "abcdef"
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upload_requires_auth(self):
        response = self.client.post("/api/files/upload/", {})
        self.assertEqual(response.status_code, 401)

    def test_upload_and_download(self):
        self.login()
        response = self.client.post(
            "/api/files/upload/",
            {"file": io.BytesIO(b"hello"), "comment": "test"},
            format="multipart"
        )
        self.assertEqual(response.status_code, 201)
        file_id = response.data["file"]["id"]
        download = self.client.get(f"/api/files/{file_id}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"hello")
