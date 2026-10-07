from django.db import migrations, models


def assign_existing_patient_numbers(apps, schema_editor):
    database = schema_editor.connection.alias
    PatientProfile = apps.get_model("patients", "PatientProfile")
    PatientNumberSequence = apps.get_model("patients", "PatientNumberSequence")

    sequence, _ = PatientNumberSequence.objects.using(database).get_or_create(
        pk=1,
        defaults={"last_value": 0},
    )
    profiles = PatientProfile.objects.using(database).order_by("pk")
    number = 0
    for profile in profiles.iterator():
        number += 1
        profile.patient_number = f"MED-{number:06d}"
        profile.save(using=database, update_fields=("patient_number",))
    sequence.last_value = number
    sequence.save(using=database, update_fields=("last_value",))


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientNumberSequence",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("last_value", models.PositiveBigIntegerField(default=0)),
            ],
            options={"db_table": "patients_patient_number_sequence"},
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="patient_number",
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="gender",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="blood_group",
            field=models.CharField(blank=True, max_length=3),
        ),
        migrations.RunPython(assign_existing_patient_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="patientprofile",
            name="patient_number",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=20,
                unique=True,
            ),
        ),
    ]
