import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.prescriptions.models import Medicine


REQUIRED_COLUMNS = {
    "medicine_id",
    "medicine_name",
    "generic_name",
    "strength",
    "dosage_form",
    "route",
    "manufacturer",
    "is_active",
}
MAX_LENGTHS = {
    "medicine_name": 180,
    "generic_name": 180,
    "strength": 100,
    "dosage_form": 80,
    "route": 80,
    "manufacturer": 180,
}
TRUTHY_VALUES = {"true", "1", "yes"}
FALSY_VALUES = {"false", "0", "no"}


class Command(BaseCommand):
    help = "Import or update medicines from a CSV file using its product name and strength."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if not csv_path.is_file():
            raise CommandError(f"Medicine CSV does not exist: {csv_path}")

        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                columns = set(reader.fieldnames or ())
                missing_columns = REQUIRED_COLUMNS - columns
                if missing_columns:
                    raise CommandError(
                        "Medicine CSV is missing required columns: "
                        + ", ".join(sorted(missing_columns))
                    )
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as error:
            raise CommandError(f"Could not read medicine CSV: {error}") from error

        prepared_rows = []
        seen_products = set()
        seen_source_ids = set()
        for row_number, row in enumerate(rows, start=2):
            values = {
                column: (row.get(column) or "").strip()
                for column in REQUIRED_COLUMNS
            }
            if not values["medicine_name"] or not values["strength"]:
                raise CommandError(
                    f"Row {row_number} must include medicine_name and strength."
                )
            if not values["medicine_id"].isdigit() or int(values["medicine_id"]) <= 0:
                raise CommandError(
                    f"Row {row_number} must include a positive integer medicine_id."
                )
            source_id = int(values["medicine_id"])
            if source_id in seen_source_ids:
                raise CommandError(f"Row {row_number} duplicates medicine_id {source_id}.")
            seen_source_ids.add(source_id)

            for column, max_length in MAX_LENGTHS.items():
                if len(values[column]) > max_length:
                    raise CommandError(
                        f"Row {row_number} has {column} longer than {max_length} characters."
                    )

            active_value = values["is_active"].lower()
            if active_value not in TRUTHY_VALUES | FALSY_VALUES:
                raise CommandError(
                    f"Row {row_number} has an unsupported is_active value: "
                    f"{values['is_active']!r}."
                )

            product_key = (
                values["medicine_name"].casefold(),
                values["strength"].casefold(),
                values["dosage_form"].casefold(),
            )
            if product_key in seen_products:
                raise CommandError(
                    f"Row {row_number} duplicates a product name, strength, and dosage form."
                )
            seen_products.add(product_key)
            prepared_rows.append(
                {
                    "key": {
                        "name": values["medicine_name"],
                        "strength": values["strength"],
                        "dosage_form": values["dosage_form"],
                    },
                    "defaults": {
                        "source_id": source_id,
                        "generic_name": values["generic_name"],
                        "route": values["route"],
                        "manufacturer": values["manufacturer"],
                        "is_active": active_value in TRUTHY_VALUES,
                    },
                }
            )

        created = 0
        updated = 0
        with transaction.atomic():
            for row in prepared_rows:
                _, was_created = Medicine.objects.update_or_create(
                    **row["key"],
                    defaults=row["defaults"],
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            example_entries_deactivated = Medicine.objects.filter(
                name__in=("Paracetamol", "Amoxicillin"),
                generic_name__in=("Paracetamol", "Amoxicillin"),
                manufacturer="",
                is_active=True,
            ).update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(prepared_rows)} rows: {created} created, "
                f"{updated} updated, {example_entries_deactivated} sample entries deactivated."
            )
        )
