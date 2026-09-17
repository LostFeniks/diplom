from pathlib import Path
from uuid import uuid4

from django.conf import settings


def get_user_storage_dir(user):
    storage_dir = Path(settings.MEDIA_ROOT) / user.storage_path
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def generate_unique_filename(original_name):
    extension = Path(original_name).suffix.lower()
    return f"{uuid4().hex}{extension}"
