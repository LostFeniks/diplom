import logging
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Sum
from django.http import FileResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .auth import require_auth, require_admin
from .models import User, StoredFile
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer, StoredFileSerializer
from .utils import ensure_user_storage, create_storage_name, safe_remove

logger = logging.getLogger("storage")


@api_view(["GET"])
@ensure_csrf_cookie
def csrf(request):
    return Response({"detail": "CSRF cookie initialized."})


@api_view(["POST"])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning("Registration validation failed: %s", serializer.errors)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user = User(
        login=data["login"],
        full_name=data["full_name"],
        email=data["email"],
        storage_path=__import__("uuid").uuid4().hex,
    )
    user.set_password(data["password"])
    user.save()
    ensure_user_storage(user)
    logger.info("User registered: id=%s login=%s", user.id, user.login)
    return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    login_value = serializer.validated_data["login"]
    user = User.objects.filter(login__iexact=login_value).first()
    if not user:
        logger.warning("Login failed: unknown login=%s", login_value)
        return Response({"error": "Неверный логин или пароль."}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.check_password(serializer.validated_data["password"]):
        logger.warning("Login failed: invalid password for login=%s", user.login)
        return Response({"error": "Неверный логин или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

    request.session.cycle_key()
    request.session["user_id"] = user.id
    logger.info("User logged in: id=%s login=%s", user.id, user.login)
    return Response({"user": UserSerializer(user).data})


@api_view(["POST"])
@require_auth
def logout(request):
    login_value = request.storage_user.login
    request.session.flush()
    logger.info("User logged out: login=%s", login_value)
    return Response({"detail": "Выход выполнен."})


@api_view(["GET"])
@require_auth
def me(request):
    return Response({"user": UserSerializer(request.storage_user).data})


@api_view(["GET"])
@require_admin
def users_list(request):
    users = User.objects.annotate(
        calculated_file_count=Count("files", distinct=True),
        calculated_storage_size=Sum("files__size"),
    )

    result = []
    for user in users:
        data = UserSerializer(user).data
        data["file_count"] = user.calculated_file_count or 0
        data["storage_size"] = user.calculated_storage_size or 0
        result.append(data)

    return Response({"users": result})


@api_view(["DELETE"])
@require_admin
def user_delete(request, user_id):
    if request.storage_user.id == user_id:
        return Response({"error": "Нельзя удалить текущего администратора."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

    storage = settings.MEDIA_ROOT / user.storage_path
    user_login = user.login
    user.delete()
    import shutil
    shutil.rmtree(storage, ignore_errors=True)
    logger.info("User deleted: id=%s login=%s", user_id, user_login)
    return Response({"detail": "Пользователь удалён."})


@api_view(["PATCH"])
@require_admin
def user_admin_toggle(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

    if "is_admin" not in request.data or not isinstance(request.data["is_admin"], bool):
        return Response({"error": "Поле is_admin должно быть boolean."}, status=status.HTTP_400_BAD_REQUEST)

    if request.storage_user.id == user.id and request.data["is_admin"] is False:
        return Response({"error": "Нельзя снять права администратора с самого себя."}, status=status.HTTP_400_BAD_REQUEST)

    user.is_admin = request.data["is_admin"]
    user.save(update_fields=["is_admin"])
    logger.info("Admin flag changed: target=%s is_admin=%s by=%s", user.login, user.is_admin, request.storage_user.login)
    return Response({"user": UserSerializer(user).data})


def resolve_target_user(request):
    if "user_id" in request.GET:
        if not request.storage_user.is_admin:
            return None, Response({"error": "Недостаточно прав для доступа к чужому хранилищу."}, status=status.HTTP_403_FORBIDDEN)
        try:
            return User.objects.get(pk=request.GET["user_id"]), None
        except User.DoesNotExist:
            return None, Response({"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)
    return request.storage_user, None


@api_view(["GET"])
@require_auth
def files_list(request):
    target, error = resolve_target_user(request)
    if error:
        return error
    files = target.files.all()
    return Response({
        "user": UserSerializer(target).data,
        "files": StoredFileSerializer(files, many=True, context={"request": request}).data,
    })


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@require_auth
def file_upload(request):
    target, error = resolve_target_user(request)
    if error:
        return error

    uploaded = request.FILES.get("file")
    comment = request.data.get("comment", "")
    if not uploaded:
        return Response({"error": "Файл не передан."}, status=status.HTTP_400_BAD_REQUEST)
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        return Response({"error": f"Максимальный размер файла: {settings.MAX_UPLOAD_SIZE} байт."}, status=status.HTTP_400_BAD_REQUEST)

    storage = ensure_user_storage(target)
    disk_name = create_storage_name(uploaded.name)
    destination = storage / disk_name

    try:
        with destination.open("wb+") as destination_file:
            for chunk in uploaded.chunks():
                destination_file.write(chunk)
        obj = StoredFile.objects.create(
            owner=target,
            original_name=Path(uploaded.name).name[:255],
            size=uploaded.size,
            comment=str(comment)[:5000],
            file_path=str(destination.relative_to(settings.MEDIA_ROOT)),
        )
    except Exception:
        safe_remove(destination)
        logger.exception("File upload failed")
        return Response({"error": "Не удалось сохранить файл."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info("File uploaded: id=%s owner=%s name=%s size=%s", obj.id, target.login, obj.original_name, obj.size)
    return Response({"file": StoredFileSerializer(obj, context={"request": request}).data}, status=status.HTTP_201_CREATED)


def get_file_for_user(request, file_id):
    try:
        obj = StoredFile.objects.select_related("owner").get(pk=file_id)
    except StoredFile.DoesNotExist:
        return None, Response({"error": "Файл не найден."}, status=status.HTTP_404_NOT_FOUND)

    if obj.owner_id != request.storage_user.id and not request.storage_user.is_admin:
        return None, Response({"error": "Нет доступа к файлу."}, status=status.HTTP_403_FORBIDDEN)
    return obj, None


@api_view(["PATCH", "DELETE"])
@require_auth
def file_update(request, file_id):
    obj, error = get_file_for_user(request, file_id)
    if error:
        return error

    if request.method == "DELETE":
        physical = settings.MEDIA_ROOT / obj.file_path
        name = obj.original_name
        obj.delete()
        safe_remove(physical)
        logger.info(
            "File deleted: id=%s name=%s by=%s",
            file_id,
            name,
            request.storage_user.login,
        )
        return Response({"detail": "Файл удалён."}, status=status.HTTP_200_OK)

    changed = []

    # Accept both names for backward compatibility with the existing frontend.
    if "name" in request.data or "original_name" in request.data:
        requested_name = request.data.get(
            "name", request.data.get("original_name", "")
        )
        name = Path(str(requested_name)).name.strip()
        if not name:
            return Response(
                {"error": "Имя файла не может быть пустым."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_suffix = Path(obj.original_name).suffix.lower()
        new_suffix = Path(name).suffix.lower()

        # If the extension is omitted, preserve the existing extension.
        if old_suffix and not new_suffix:
            name = f"{name}{old_suffix}"
            new_suffix = old_suffix

        # Do not allow changing the file type during a rename.
        if old_suffix and new_suffix != old_suffix:
            return Response(
                {"error": f"Расширение файла нельзя изменять. Используйте: {old_suffix}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_path = settings.MEDIA_ROOT / obj.file_path
        new_path = old_path.with_name(name)

        if new_path != old_path and new_path.exists():
            return Response(
                {"error": "Файл с таким именем уже существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_path != old_path:
            try:
                old_path.rename(new_path)
            except OSError:
                logger.exception("File rename failed: id=%s", obj.id)
                return Response(
                    {"error": "Не удалось переименовать файл."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            obj.file_path = str(new_path.relative_to(settings.MEDIA_ROOT))
            changed.append("file_path")

        obj.original_name = name[:255]
        changed.append("original_name")

    if "comment" in request.data:
        obj.comment = str(request.data["comment"])[:5000]
        changed.append("comment")

    if not changed:
        return Response(
            {"error": "Нет данных для изменения."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    obj.save(update_fields=list(dict.fromkeys(changed)))
    logger.info(
        "File updated: id=%s fields=%s by=%s",
        obj.id,
        changed,
        request.storage_user.login,
    )
    return Response(
        {"file": StoredFileSerializer(obj, context={"request": request}).data},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@require_auth
def file_download(request, file_id):
    obj, error = get_file_for_user(request, file_id)
    if error:
        return error

    physical = settings.MEDIA_ROOT / obj.file_path
    if not physical.is_file():
        logger.error("Physical file missing: id=%s path=%s", obj.id, physical)
        return Response({"error": "Физический файл отсутствует на сервере."}, status=status.HTTP_404_NOT_FOUND)

    obj.mark_downloaded()
    logger.info("File downloaded: id=%s name=%s by=%s", obj.id, obj.original_name, request.storage_user.login)
    response = FileResponse(open(physical, "rb"), as_attachment=True, filename=obj.original_name)
    return response


@api_view(["POST"])
@require_auth
def file_share(request, file_id):
    obj, error = get_file_for_user(request, file_id)
    if error:
        return error
    return Response({
        "public_url": request.build_absolute_uri(f"/api/shared/{obj.public_token}/")
    })


@api_view(["GET"])
def public_download(request, token):
    try:
        obj = StoredFile.objects.get(public_token=token)
    except StoredFile.DoesNotExist:
        return Response({"error": "Файл не найден."}, status=status.HTTP_404_NOT_FOUND)

    physical = settings.MEDIA_ROOT / obj.file_path
    if not physical.is_file():
        return Response({"error": "Физический файл отсутствует на сервере."}, status=status.HTTP_404_NOT_FOUND)

    obj.mark_downloaded()
    logger.info("Public file download: id=%s name=%s", obj.id, obj.original_name)
    return FileResponse(open(physical, "rb"), as_attachment=True, filename=obj.original_name)
