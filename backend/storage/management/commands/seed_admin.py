from django.core.management.base import BaseCommand
from storage.models import User
from storage.utils import ensure_user_storage
import uuid

class Command(BaseCommand):
    help = "Creates the default admin user if it does not exist."

    def handle(self, *args, **options):
        user = User.objects.filter(login="admin").first()
        if user:
            if not user.is_admin:
                user.is_admin = True
                user.save(update_fields=["is_admin"])
            ensure_user_storage(user)
            self.stdout.write(self.style.SUCCESS("admin user already exists; admin flag ensured."))
            return

        user = User(
            login="admin",
            full_name="Администратор",
            email="admin@example.com",
            is_admin=True,
            storage_path=uuid.uuid4().hex,
        )
        user.set_password("Admin123!")
        user.save()
        ensure_user_storage(user)
        self.stdout.write(self.style.SUCCESS("Created admin: login=admin password=Admin123!"))
