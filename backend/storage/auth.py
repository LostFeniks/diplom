from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .models import User

def get_session_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return None

def require_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_session_user(request)
        if not user:
            return Response({"error": "Требуется аутентификация."}, status=status.HTTP_401_UNAUTHORIZED)
        request.storage_user = user
        return view_func(request, *args, **kwargs)
    return wrapper

def require_admin(view_func):
    @wraps(view_func)
    @require_auth
    def wrapper(request, *args, **kwargs):
        if not request.storage_user.is_admin:
            return Response({"error": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return wrapper
