import os
import uuid
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone


class User(models.Model):
    login = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_admin = models.BooleanField(default=False)
    storage_path = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def storage_size(self):
        return sum(f.size for f in self.files.all())

    def __str__(self):
        return self.login


class StoredFile(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="files")
    original_name = models.CharField(max_length=255)
    size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)
    file_path = models.CharField(max_length=1000)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ["-uploaded_at"]

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1]

    def mark_downloaded(self):
        self.last_downloaded_at = timezone.now()
        self.save(update_fields=["last_downloaded_at"])

    def __str__(self):
        return self.original_name
