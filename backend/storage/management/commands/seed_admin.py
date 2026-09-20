import os
import uuid

from django.core.management.base import BaseCommand, CommandError

from storage.models import User
from storage.utils import ensure_user_storage


class Command(BaseCommand):
    help = "Creates the default admin user if it does not exist."

    def handle(self, *args, **options):
        login = os.getenv("ADMIN_LOGIN", "admin")
        password = os.getenv("ADMIN_PASSWORD")
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        full_name = os.getenv("ADMIN_FULL_NAME", "Администратор")

        if not password:
            raise CommandError(
                "Не задан ADMIN_PASSWORD в файле .env. "
                "Укажите пароль администратора перед запуском seed_admin."
            )

        user = User.objects.filter(login__iexact=login).first()
        if user:
            if not user.is_admin:
                user.is_admin = True
                user.save(update_fields=["is_admin"])
            ensure_user_storage(user)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Пользователь {user.login} уже существует; права администратора обеспечены."
                )
            )
            return

        user = User(
            login=login,
            full_name=full_name,
            email=email,
            is_admin=True,
            storage_path=uuid.uuid4().hex,
        )
        user.set_password(password)
        user.save()
        ensure_user_storage(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Администратор создан: login={login}"
            )
        )
