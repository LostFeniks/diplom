import os
import uuid
from pathlib import Path

from django.conf import settings
from django.utils.text import get_valid_filename


def ensure_user_storage(user):
    """Create and return the user's physical storage directory."""
    path = Path(settings.MEDIA_ROOT) / user.storage_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_storage_name(original_name):
    """Generate a unique physical filename while preserving the extension."""
    safe = get_valid_filename(Path(original_name).name)
    extension = Path(safe).suffix.lower()
    return f"{uuid.uuid4().hex}{extension}"


def safe_remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
