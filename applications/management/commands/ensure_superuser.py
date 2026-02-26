"""
Create or reset a default superuser for prototype/demo environments.

Runs automatically on Railway deploy via nixpacks.toml start command.
Prints detailed diagnostics to help debug Railway DB issues.
"""

import sys
import traceback

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create or reset prototype superuser (Admin/Admin123)"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "Admin"
        password = "Admin123"

        # Debug: show what table Django expects
        self.stdout.write(f"User model: {User}")
        self.stdout.write(f"DB table: {User._meta.db_table}")

        # Debug: check if the table exists
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE tablename = %s",
                [User._meta.db_table],
            )
            row = cursor.fetchone()
            if row:
                self.stdout.write(f"Table '{User._meta.db_table}' exists")
                # Check columns
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                    [User._meta.db_table],
                )
                cols = [r[0] for r in cursor.fetchall()]
                self.stdout.write(f"Columns: {', '.join(cols)}")
                # Count existing users
                cursor.execute(f"SELECT COUNT(*) FROM {User._meta.db_table}")
                count = cursor.fetchone()[0]
                self.stdout.write(f"Existing users: {count}")
            else:
                self.stderr.write(self.style.ERROR(f"Table '{User._meta.db_table}' does NOT exist!"))
                self.stderr.write("Migration likely failed. Check 'python manage.py showmigrations'")
                return

        # Debug: check migration state
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT app, name FROM django_migrations WHERE app = 'applications' ORDER BY id"
            )
            migrations = cursor.fetchall()
            self.stdout.write(f"Applied migrations for 'applications': {migrations}")

        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": "admin@thelandbank.org", "is_staff": True, "is_superuser": True},
            )
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()

            if created:
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' password reset and privileges confirmed"))
        except Exception:
            self.stderr.write(self.style.ERROR("Failed to create/update superuser:"))
            traceback.print_exc(file=sys.stderr)
