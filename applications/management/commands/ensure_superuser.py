"""
Create a default superuser for prototype/demo environments.

Idempotent: skips if the user already exists.
Runs automatically on Railway deploy via nixpacks.toml start command.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create default superuser (Admin/Admin123) if it does not exist"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "Admin"
        password = "Admin123"

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists — skipping"))
            return

        User.objects.create_superuser(username=username, email="admin@thelandbank.org", password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created"))
