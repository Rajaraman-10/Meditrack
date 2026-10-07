from django.db import migrations, models
from django.utils.text import slugify


def populate_department_codes(apps, schema_editor):
    Department = apps.get_model("clinics", "Department")
    for department in Department.objects.order_by("pk").iterator():
        base = slugify(department.name).upper().replace("-", "_")[:17] or "DEPT"
        department.code = f"{base}_{department.pk}"
        department.save(update_fields=("code",))


class Migration(migrations.Migration):

    dependencies = [
        ("clinics", "0002_doctoravailability_doctor_availability_weekday_range_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="code",
            field=models.CharField(blank=True, max_length=24, null=True),
        ),
        migrations.RunPython(populate_department_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="department",
            name="code",
            field=models.CharField(blank=True, max_length=24, unique=True),
        ),
    ]
