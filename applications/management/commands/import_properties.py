"""
Management command: Import properties from a CSV file.

Usage:
    python manage.py import_properties path/to/file.csv
    python manage.py import_properties path/to/file.csv --replace
    python manage.py import_properties path/to/file.csv --batch "February 2026"

CSV must have columns: address, parcel_id, program (and optionally price).
Column names are flexible — see csv_import.py for accepted variations.
"""

from django.core.management.base import BaseCommand

from applications.csv_import import import_properties_from_csv


class Command(BaseCommand):
    help = "Import Land Bank properties from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the CSV file to import")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Mark all currently available properties as withdrawn before import",
        )
        parser.add_argument(
            "--batch",
            default="",
            help="Label for this import batch (defaults to timestamp)",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]

        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                text = f.read()
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        result = import_properties_from_csv(
            text,
            replace_existing=options["replace"],
            batch_label=options["batch"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created: {result['created']}  "
                f"Updated: {result['updated']}  "
                f"Skipped: {result['skipped']}"
            )
        )

        if result["errors"]:
            self.stdout.write(self.style.WARNING(f"\n{len(result['errors'])} error(s):"))
            for err in result["errors"]:
                self.stdout.write(self.style.WARNING(f"  - {err}"))
