from django.contrib import admin
from .models import User, StoredFile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "login", "full_name", "email", "is_admin", "storage_path")
    search_fields = ("login", "full_name", "email")
    list_filter = ("is_admin",)

@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "owner", "size", "uploaded_at", "last_downloaded_at")
    search_fields = ("original_name", "owner__login")
