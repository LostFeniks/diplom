import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import serializers
from .models import User, StoredFile

LOGIN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{3,19}$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{6,}$")


class RegisterSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=20)
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_login(self, value):
        if not LOGIN_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Логин: только латинские буквы и цифры, первый символ — буква, длина 4–20 символов."
            )
        if User.objects.filter(login__iexact=value).exists():
            raise serializers.ValidationError("Такой логин уже зарегистрирован.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Такой email уже зарегистрирован.")
        return value

    def validate_password(self, value):
        if not PASSWORD_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Пароль должен быть не менее 6 символов и содержать заглавную букву, цифру и специальный символ."
            )
        return value


class UserSerializer(serializers.ModelSerializer):
    file_count = serializers.IntegerField(read_only=True)
    storage_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "login", "full_name", "email", "is_admin", "storage_path", "file_count", "storage_size", "created_at"]
        read_only_fields = ["id", "storage_path", "file_count", "storage_size", "created_at"]


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)


class StoredFileSerializer(serializers.ModelSerializer):
    public_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    last_downloaded_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = StoredFile
        fields = [
            "id", "original_name", "comment", "size",
            "uploaded_at", "last_downloaded_at",
            "public_url", "download_url"
        ]
        read_only_fields = ["id", "size", "uploaded_at", "last_downloaded_at", "public_url", "download_url"]

    def get_public_url(self, obj):
        request = self.context.get("request")
        path = f"/api/shared/{obj.public_token}/"
        return request.build_absolute_uri(path) if request else path

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/files/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path
