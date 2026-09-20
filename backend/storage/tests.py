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

@override_settings(MEDIA_ROOT="/tmp/diplom-test-media", MAX_UPLOAD_SIZE=3)
class StorageValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User(
            login="tester2",
            full_name="Test User 2",
            email="tester2@example.com",
            storage_path=uuid.uuid4().hex,
        )
        self.user.set_password("Test123!")
        self.user.save()

    def login(self):
        response = self.client.post(
            "/api/auth/login/",
            {"login": self.user.login, "password": "Test123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_server_registration_validation(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "login": "1",
                "full_name": "Bad User",
                "email": "bad@example.com",
                "password": "123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("login", response.data["errors"])
        self.assertIn("password", response.data["errors"])

    def test_upload_size_limit(self):
        self.login()
        response = self.client.post(
            "/api/files/upload/",
            {"file": io.BytesIO(b"1234"), "comment": "too large"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(MAX_UPLOAD_SIZE=100)
    def test_rename_preserves_extension_and_delete(self):
        self.login()
        response = self.client.post(
            "/api/files/upload/",
            {"file": io.BytesIO(b"hello"), "comment": "test"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        file_id = response.data["file"]["id"]

        response = self.client.patch(
            f"/api/files/{file_id}/",
            {"original_name": "renamed", "comment": "updated"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["file"]["original_name"], "renamed")

        response = self.client.delete(f"/api/files/{file_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StoredFile.objects.filter(pk=file_id).exists())
