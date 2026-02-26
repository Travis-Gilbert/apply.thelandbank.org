"""
Create or reset a default superuser for prototype/demo environments.

Runs automatically on Railway deploy via nixpacks.toml start command.
If the user exists, resets password and ensures superuser + staff flags.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset prototype superuser (Admin/Admin123)"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "Admin"
        password = "Admin123"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": "admin@thelandbank.org", "is_staff": True, "is_superuser": True},
        )

        # Always reset password and ensure privileges on every deploy
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' password reset and privileges confirmed"))
