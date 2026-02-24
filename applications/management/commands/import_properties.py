"""
Management command: Import properties from a CSV or Excel file.

Usage:
    python manage.py import_properties path/to/file.csv
    python manage.py import_properties path/to/file.xlsx
    python manage.py import_properties path/to/file.xlsx --replace
    python manage.py import_properties path/to/file.csv --batch "February 2026"

CSV must have columns: address, parcel_id, program (and optionally price).
Excel (.xlsx) expects FileMaker export format with Street Address, GCLB Owned, etc.
"""

from django.core.management.base import BaseCommand

from applications.csv_import import (
    import_properties_from_csv,
    import_properties_from_excel,
)


class Command(BaseCommand):
    help = "Import Land Bank properties from a CSV or Excel (.xlsx) file."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the CSV or Excel file to import")
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
        file_path = options["file"]
        is_excel = file_path.lower().endswith((".xlsx", ".xls", ".xlsm"))

        if is_excel:
            result = import_properties_from_excel(
                file_path,
                replace_existing=options["replace"],
                batch_label=options["batch"],
            )
        else:
            try:
                with open(file_path, encoding="utf-8-sig") as f:
                    text = f.read()
            except FileNotFoundError:
                self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
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
            for err in result["errors"][:20]:
                self.stdout.write(self.style.WARNING(f"  - {err}"))
            if len(result["errors"]) > 20:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ... and {len(result['errors']) - 20} more"
                    )
                )
