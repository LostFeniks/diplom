import logging
import shutil
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db.models import Count, Sum
from django.http import FileResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .auth import get_session_user, require_admin, require_auth
from .models import StoredFile, User
from .serializers import StoredFileSerializer, UserSerializer
from .utils import generate_unique_filename, get_user_storage_dir


logger = logging.getLogger("storage")


def error_response(message, status_code):
    return Response(
        {"error": message},
        status=status_code,
    )


# ============================================================
# CSRF
# ============================================================

@api_view(["GET"])
@ensure_csrf_cookie
def csrf(request):
    return Response(
        {"message": "CSRF cookie установлена."},
        status=status.HTTP_200_OK,
    )


# ============================================================
# AUTH
# ============================================================

@api_view(["POST"])
def register(request):
    login = str(request.data.get("login", "")).strip()
    full_name = str(request.data.get("full_name", "")).strip()
    email = str(request.data.get("email", "")).strip()
    password = str(request.data.get("password", ""))

    errors = {}

    if not login:
        errors["login"] = "Введите логин."

    if not full_name:
        errors["full_name"] = "Введите полное имя."

    if not email:
        errors["email"] = "Введите email."

    if not password:
        errors["password"] = "Введите пароль."

    if errors:
        return error_response(
            {
                "message": "Проверьте заполненные поля.",
                "fields": errors,
            },
            status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(login__iexact=login).exists():
        return error_response(
            "Пользователь с таким логином уже существует.",
            status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email__iexact=email).exists():
        return error_response(
            "Пользователь с таким email уже существует.",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.create_user(
            login=login,
            full_name=full_name,
            email=email,
            password=password,
        )
    except ValueError as exc:
        return error_response(
            str(exc),
            status.HTTP_400_BAD_REQUEST,
        )

    logger.info(
        "User registered: id=%s login=%s",
        user.id,
        user.login,
    )

    return Response(
        UserSerializer(
            user,
            context={"request": request},
        ).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def login(request):
    login_value = str(request.data.get("login", "")).strip()
    password = str(request.data.get("password", ""))

    if not login_value or not password:
        return error_response(
            "Введите логин и пароль.",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(login__iexact=login_value)
    except User.DoesNotExist:
        logger.warning(
            "Failed login attempt: login=%s",
            login_value,
        )
        return error_response(
            "Неверный логин или пароль.",
            status.HTTP_401_UNAUTHORIZED,
        )

    if not user.check_password(password):
        logger.warning(
            "Failed login attempt: login=%s",
            login_value,
        )
        return error_response(
            "Неверный логин или пароль.",
            status.HTTP_401_UNAUTHORIZED,
        )

    request.session.cycle_key()
    request.session["user_id"] = user.id
    request.session.save()

    logger.info(
        "User logged in: id=%s login=%s",
        user.id,
        user.login,
    )

    return Response(
        UserSerializer(
            user,
            context={"request": request},
        ).data,
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def logout(request):
    user = get_session_user(request)

    if user:
        logger.info(
            "User logged out: id=%s login=%s",
            user.id,
            user.login,
        )

    request.session.flush()

    return Response(
        {"message": "Вы успешно вышли из системы."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def me(request):
    user = get_session_user(request)

    if user is None:
        return error_response(
            "Пользователь не авторизован.",
            status.HTTP_401_UNAUTHORIZED,
        )

    return Response(
        UserSerializer(
            user,
            context={"request": request},
        ).data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# ADMIN — USERS
# ============================================================

@api_view(["GET"])
@require_admin
def users_list(request):
    users = (
        User.objects
        .annotate(
            calculated_storage_size=Sum("files__size"),
            calculated_file_count=Count("files"),
        )
        .order_by("id")
    )

    result = []

    for user in users:
        data = UserSerializer(
            user,
            context={"request": request},
        ).data

        data["storage_size"] = user.calculated_storage_size or 0
        data["file_count"] = user.calculated_file_count or 0

        result.append(data)

    return Response(
        result,
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@require_admin
def user_delete(request, user_id):
    current_user = request.storage_user

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response(
            "Пользователь не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if user.id == current_user.id:
        return error_response(
            "Нельзя удалить текущего администратора.",
            status.HTTP_400_BAD_REQUEST,
        )

    storage_dir = get_user_storage_dir(user)

    user_id_value = user.id
    login_value = user.login

    user.delete()

    if storage_dir.exists():
        try:
            shutil.rmtree(storage_dir)
        except OSError:
            logger.exception(
                "Could not remove storage directory for user id=%s",
                user_id_value,
            )

    logger.info(
        "User deleted: id=%s login=%s by admin id=%s",
        user_id_value,
        login_value,
        current_user.id,
    )

    return Response(
        {"message": "Пользователь удалён."},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@require_admin
def user_admin_update(request, user_id):
    current_user = request.storage_user

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return error_response(
            "Пользователь не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if "is_admin" not in request.data:
        return error_response(
            "Необходимо передать поле is_admin.",
            status.HTTP_400_BAD_REQUEST,
        )

    value = request.data.get("is_admin")

    if not isinstance(value, bool):
        return error_response(
            "Поле is_admin должно иметь значение true или false.",
            status.HTTP_400_BAD_REQUEST,
        )

    if user.id == current_user.id and value is False:
        return error_response(
            "Нельзя снять права администратора у текущего пользователя.",
            status.HTTP_400_BAD_REQUEST,
        )

    user.is_admin = value
    user.save(update_fields=["is_admin"])

    logger.info(
        "Admin flag changed: user_id=%s is_admin=%s by admin_id=%s",
        user.id,
        user.is_admin,
        current_user.id,
    )

    return Response(
        UserSerializer(
            user,
            context={"request": request},
        ).data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# STORAGE HELPERS
# ============================================================

def get_requested_storage_user(request):
    """
    Определяет пользователя, чьё файловое хранилище требуется открыть.

    Обычный пользователь может работать только со своим хранилищем.
    Администратор может указать user_id и работать с хранилищем
    другого пользователя.
    """

    current_user = request.storage_user

    user_id = request.query_params.get("user_id")

    if user_id:
        try:
            requested_user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, ValueError):
            return None, error_response(
                "Пользователь не найден.",
                status.HTTP_404_NOT_FOUND,
            )

        if (
            requested_user.id != current_user.id
            and not current_user.is_admin
        ):
            return None, error_response(
                "Нет доступа к хранилищу другого пользователя.",
                status.HTTP_403_FORBIDDEN,
            )

        return requested_user, None

    return current_user, None


# ============================================================
# FILES — LIST
# ============================================================

@api_view(["GET"])
@require_auth
def files_list(request):
    user, error = get_requested_storage_user(request)

    if error:
        return error

    files = (
        StoredFile.objects
        .filter(owner=user)
        .order_by("-uploaded_at")
    )

    return Response(
        StoredFileSerializer(
            files,
            many=True,
            context={"request": request},
        ).data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# FILES — UPLOAD
# ============================================================

@api_view(["POST"])
@require_auth
def file_upload(request):
    user, error = get_requested_storage_user(request)

    if error:
        return error

    uploaded_file = request.FILES.get("file")

    if uploaded_file is None:
        return error_response(
            "Файл не был передан.",
            status.HTTP_400_BAD_REQUEST,
        )

    comment = str(
        request.data.get("comment", "")
    ).strip()

    storage_dir = get_user_storage_dir(user)

    original_name = Path(uploaded_file.name).name

    if not original_name:
        return error_response(
            "Некорректное имя файла.",
            status.HTTP_400_BAD_REQUEST,
        )

    # Физическое имя файла не содержит исходного имени.
    physical_name = generate_unique_filename(original_name)

    physical_path = storage_dir / physical_name

    try:
        with physical_path.open("wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

    except OSError:
        logger.exception(
            "File upload failed for user id=%s",
            user.id,
        )

        return error_response(
            "Не удалось сохранить файл.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        stored_file = StoredFile.objects.create(
            owner=user,
            original_name=original_name,
            size=uploaded_file.size,
            comment=comment,
            file_path=str(
                physical_path.relative_to(
                    settings.MEDIA_ROOT
                )
            ),
        )
    except Exception:
        # Если запись в БД не создалась,
        # удаляем уже сохранённый физический файл.
        try:
            if physical_path.exists():
                physical_path.unlink()
        except OSError:
            logger.exception(
                "Could not rollback uploaded file: %s",
                physical_path,
            )

        logger.exception(
            "Database record creation failed for uploaded file."
        )

        return error_response(
            "Не удалось сохранить информацию о файле.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    logger.info(
        "File uploaded: id=%s user_id=%s name=%s size=%s",
        stored_file.id,
        user.id,
        original_name,
        uploaded_file.size,
    )

    return Response(
        StoredFileSerializer(
            stored_file,
            context={"request": request},
        ).data,
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# FILES — UPDATE
# ============================================================

@api_view(["PATCH"])
@require_auth
def file_update(request, file_id):
    current_user = request.storage_user

    try:
        stored_file = (
            StoredFile.objects
            .select_related("owner")
            .get(id=file_id)
        )
    except StoredFile.DoesNotExist:
        return error_response(
            "Файл не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if (
        stored_file.owner_id != current_user.id
        and not current_user.is_admin
    ):
        return error_response(
            "Нет доступа к этому файлу.",
            status.HTTP_403_FORBIDDEN,
        )

    changed_fields = []

    # Переименование
    if "name" in request.data:
        new_name = Path(
            str(request.data.get("name", "")).strip()
        ).name

        if not new_name:
            return error_response(
                "Имя файла не может быть пустым.",
                status.HTTP_400_BAD_REQUEST,
            )

        old_full_path = (
            settings.MEDIA_ROOT
            / stored_file.file_path
        )

        new_full_path = old_full_path.with_name(new_name)

        if (
            new_full_path != old_full_path
            and new_full_path.exists()
        ):
            return error_response(
                "Файл с таким именем уже существует.",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_full_path.rename(new_full_path)
        except OSError:
            logger.exception(
                "File rename failed: file_id=%s",
                stored_file.id,
            )

            return error_response(
                "Не удалось переименовать файл.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        stored_file.original_name = new_name
        stored_file.file_path = str(
            new_full_path.relative_to(
                settings.MEDIA_ROOT
            )
        )

        changed_fields.extend(
            ["original_name", "file_path"]
        )

    # Изменение комментария
    if "comment" in request.data:
        stored_file.comment = str(
            request.data.get("comment", "")
        ).strip()

        changed_fields.append("comment")

    if not changed_fields:
        return error_response(
            "Не указаны данные для изменения.",
            status.HTTP_400_BAD_REQUEST,
        )

    stored_file.save(
        update_fields=changed_fields
    )

    logger.info(
        "File updated: id=%s by user_id=%s",
        stored_file.id,
        current_user.id,
    )

    return Response(
        StoredFileSerializer(
            stored_file,
            context={"request": request},
        ).data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# FILES — DELETE
# ============================================================

@api_view(["DELETE"])
@require_auth
def file_delete(request, file_id):
    current_user = request.storage_user

    try:
        stored_file = (
            StoredFile.objects
            .select_related("owner")
            .get(id=file_id)
        )
    except StoredFile.DoesNotExist:
        return error_response(
            "Файл не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if (
        stored_file.owner_id != current_user.id
        and not current_user.is_admin
    ):
        return error_response(
            "Нет доступа к этому файлу.",
            status.HTTP_403_FORBIDDEN,
        )

    full_path = (
        settings.MEDIA_ROOT
        / stored_file.file_path
    )

    file_id_value = stored_file.id
    file_name = stored_file.original_name

    stored_file.delete()

    try:
        if full_path.exists():
            full_path.unlink()
    except OSError:
        logger.exception(
            "Could not delete physical file: id=%s",
            file_id_value,
        )

    logger.info(
        "File deleted: id=%s name=%s by user_id=%s",
        file_id_value,
        file_name,
        current_user.id,
    )

    return Response(
        {"message": "Файл удалён."},
        status=status.HTTP_200_OK,
    )


# ============================================================
# FILES — DOWNLOAD
# ============================================================

@api_view(["GET"])
@require_auth
def file_download(request, file_id):
    current_user = request.storage_user

    try:
        stored_file = (
            StoredFile.objects
            .select_related("owner")
            .get(id=file_id)
        )
    except StoredFile.DoesNotExist:
        return error_response(
            "Файл не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if (
        stored_file.owner_id != current_user.id
        and not current_user.is_admin
    ):
        return error_response(
            "Нет доступа к этому файлу.",
            status.HTTP_403_FORBIDDEN,
        )

    full_path = (
        settings.MEDIA_ROOT
        / stored_file.file_path
    )

    if not full_path.exists() or not full_path.is_file():
        return error_response(
            "Физический файл не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    stored_file.last_downloaded_at = timezone.now()
    stored_file.save(
        update_fields=["last_downloaded_at"]
    )

    logger.info(
        "File downloaded: id=%s name=%s by user_id=%s",
        stored_file.id,
        stored_file.original_name,
        current_user.id,
    )

    return FileResponse(
        full_path.open("rb"),
        as_attachment=True,
        filename=stored_file.original_name,
    )


# ============================================================
# FILES — PUBLIC SHARE
# ============================================================

@api_view(["POST"])
@require_auth
def file_share(request, file_id):
    current_user = request.storage_user

    try:
        stored_file = (
            StoredFile.objects
            .select_related("owner")
            .get(id=file_id)
        )
    except StoredFile.DoesNotExist:
        return error_response(
            "Файл не найден.",
            status.HTTP_404_NOT_FOUND,
        )

    if (
        stored_file.owner_id != current_user.id
        and not current_user.is_admin
    ):
        return error_response(
            "Нет доступа к этому файлу.",
            status.HTTP_403_FORBIDDEN,
        )

    if request.data.get("regenerate") is True:
        stored_file.public_token = uuid4()
        stored_file.save(
            update_fields=["public_token"]
        )

    serializer = StoredFileSerializer(
        stored_file,
        context={"request": request},
    )

    return Response(
        {
            "public_url": serializer.data["public_url"],
            "token": str(stored_file.public_token),
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# PUBLIC FILE DOWNLOAD
# ============================================================

@api_view(["GET"])
def public_file_download(request, token):
    try:
        stored_file = StoredFile.objects.get(
            public_token=token
        )
    except StoredFile.DoesNotExist:
        raise Http404("Файл не найден.")

    full_path = (
        settings.MEDIA_ROOT
        / stored_file.file_path
    )

    if not full_path.exists() or not full_path.is_file():
        raise Http404("Физический файл не найден.")

    stored_file.last_downloaded_at = timezone.now()
    stored_file.save(
        update_fields=["last_downloaded_at"]
    )

    logger.info(
        "Public file downloaded: id=%s name=%s",
        stored_file.id,
        stored_file.original_name,
    )

    return FileResponse(
        full_path.open("rb"),
        as_attachment=True,
        filename=stored_file.original_name,
    )