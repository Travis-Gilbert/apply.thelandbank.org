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

        # Debug: check if the table exists (backend-agnostic)
        table_names = set(connection.introspection.table_names())
        if User._meta.db_table not in table_names:
            self.stderr.write(self.style.ERROR(f"Table '{User._meta.db_table}' does NOT exist!"))
            self.stderr.write("Migration likely failed. Check 'python manage.py showmigrations'")
            return

        self.stdout.write(f"Table '{User._meta.db_table}' exists")
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, User._meta.db_table)
        self.stdout.write(f"Columns: {', '.join(col.name for col in columns)}")
        self.stdout.write(f"Existing users: {User.objects.count()}")

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
