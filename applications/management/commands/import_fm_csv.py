"""
Management command: import_fm_csv

Imports property listings from FileMaker-formatted CSV exports into the
Property model, powering the address autocomplete on the buyer-facing form.

Handles two file formats:
  --program featured_homes   Expects FileMaker Featured Homes export
  --program ready_for_rehab  Expects FileMaker Ready for Rehab export

FileMaker column -> Property field mapping:
  Parc_Id          -> parcel_id
  Address Full_c   -> address  (strips embedded newlines)
  FH_Asking Price  -> listing_price (falls back to Parc_Asking_Price)

Filtering:
  Featured Homes : excludes nothing (no "Sold" status exists in export)
  Ready for Rehab: excludes status == "Dropped"

Usage:
  python manage.py import_fm_csv featured_homes path/to/featured_homes.csv
  python manage.py import_fm_csv ready_for_rehab path/to/r4r.csv --replace
  python manage.py import_fm_csv ready_for_rehab path/to/r4r.csv --dry-run

Options:
  --replace   Withdraw all current available listings for this program before
              import (use when doing a full weekly refresh)
  --dry-run   Parse and validate without writing to the database
"""

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


# Statuses that mean "this property should not be listed"
EXCLUDED_STATUSES = {
    "Dropped",
    "Sold",
}

# Column names in the FileMaker export that hold the asking price.
# We try them in order and take the first non-empty, non-zero value.
PRICE_COLUMNS = ["FH_Asking Price", "Parc_Asking_Price"]

# Status column name per program
STATUS_COLUMN = {
    "featured_homes": "FH_Status",
    "ready_for_rehab": "R4R Status",
}


def _clean_address(raw):
    """
    Normalize a FileMaker address field for storage and display.

    FileMaker exports multiline addresses with embedded newlines:
      "1009 W DAYTON ST\nFLINT, MI 48504"
    We flatten these to a single line:
      "1009 W DAYTON ST, FLINT, MI 48504"
    """
    if not raw:
        return ""
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")
    parts = [p.strip() for p in cleaned.split("\n") if p.strip()]
    return ", ".join(parts)


def _parse_price(row, columns):
    """
    Extract listing price from a CSV row.

    Tries each column in order; returns the first valid positive Decimal.
    Skips zeros (FileMaker exports 0 for unlisted prices).
    """
    for col in columns:
        raw = row.get(col, "").strip()
        if not raw:
            continue
        cleaned = raw.replace("$", "").replace(",", "").strip()
        try:
            value = Decimal(cleaned)
            if value > 0:
                return value
        except InvalidOperation:
            continue
    return None


class Command(BaseCommand):
    help = "Import FileMaker CSV property listings into the Property model"

    def add_arguments(self, parser):
        parser.add_argument(
            "program",
            choices=["featured_homes", "ready_for_rehab"],
            help="Which program this CSV belongs to",
        )
        parser.add_argument(
            "csv_file",
            help="Path to the FileMaker CSV export",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            default=False,
            help=(
                "Withdraw all current available listings for this program "
                "before importing. Use for weekly full-refresh runs."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and validate without writing to the database",
        )

    def handle(self, *args, **options):
        from applications.models import Property

        program = options["program"]
        csv_path = options["csv_file"]
        replace = options["replace"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no database writes"))

        # Read the CSV
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Could not read CSV: {e}")

        # Validate required columns exist
        if not rows:
            raise CommandError("CSV file is empty or has no data rows")

        sample = rows[0]
        missing = []
        for col in ("Parc_Id", "Address Full_c"):
            if col not in sample:
                missing.append(col)
        if missing:
            raise CommandError(
                f"Missing required columns: {', '.join(missing)}\n"
                f"Found: {', '.join(sample.keys())}"
            )

        status_col = STATUS_COLUMN[program]
        if status_col not in sample:
            self.stdout.write(
                self.style.WARNING(
                    f"Status column '{status_col}' not found - "
                    "no filtering by status will be applied"
                )
            )
            status_col = None

        batch_label = (
            f"fm-{program[:3]}-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
        )

        # Counters
        created = updated = skipped_status = skipped_no_id = skipped_no_addr = errors = 0

        # Optionally withdraw existing listings for this program
        if replace and not dry_run:
            withdrawn = Property.objects.filter(
                program_type=program,
                status=Property.Status.AVAILABLE,
            ).update(status=Property.Status.WITHDRAWN)
            self.stdout.write(f"Withdrew {withdrawn} existing {program} listings")

        for row_num, row in enumerate(rows, start=2):
            parcel_id = row.get("Parc_Id", "").strip()
            if not parcel_id:
                skipped_no_id += 1
                continue

            raw_address = row.get("Address Full_c", "").strip()
            address = _clean_address(raw_address)
            if not address:
                skipped_no_addr += 1
                continue

            # Filter by status
            if status_col:
                status_val = row.get(status_col, "").strip()
                if status_val in EXCLUDED_STATUSES:
                    skipped_status += 1
                    continue

            listing_price = _parse_price(row, PRICE_COLUMNS)

            if dry_run:
                price_str = f"${listing_price:,.0f}" if listing_price else "no price"
                self.stdout.write(
                    f"  Row {row_num}: {parcel_id} | {address} | {price_str}"
                )
                created += 1
                continue

            try:
                _, was_created = Property.objects.update_or_create(
                    parcel_id=parcel_id,
                    defaults={
                        "address": address,
                        "program_type": program,
                        "listing_price": listing_price,
                        "status": Property.Status.AVAILABLE,
                        "csv_batch": batch_label,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Row {row_num} ({parcel_id}): {e}")
                )
                errors += 1

        # Summary
        verb = "Would import" if dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {program.replace('_', ' ').title()} - "
                f"{created} created, {updated} updated | "
                f"skipped: {skipped_status} (status), "
                f"{skipped_no_id} (no parcel ID), "
                f"{skipped_no_addr} (no address) | "
                f"{errors} errors"
            )
        )
        if errors:
            self.stdout.write(
                self.style.WARNING("Review errors above before next import run")
            )
