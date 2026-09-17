from django.urls import path
from . import views

urlpatterns = [
    path("csrf/", views.csrf),
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/logout/", views.logout),
    path("auth/me/", views.me),

    path("users/", views.users_list),
    path("users/<int:user_id>/", views.user_delete),
    path("users/<int:user_id>/admin/", views.user_admin_update),

    path("files/", views.files_list),
    path("files/upload/", views.file_upload),
    path("files/<int:file_id>/", views.file_update),
    path("files/<int:file_id>/download/", views.file_download),
    path("files/<int:file_id>/share/", views.file_share),
    path("shared/<uuid:token>/", views.public_file_download),
]
