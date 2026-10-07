from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def release_existing_prescriptions(apps, schema_editor):
    Prescription = apps.get_model("prescriptions", "Prescription")
    Prescription.objects.update(
        status="released",
        released_at=django.utils.timezone.now(),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_billing_role"),
        ("prescriptions", "0004_medicine_source_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="prescription",
            name="status",
            field=models.CharField(
                choices=[
                    ("payment_pending", "Payment pending"),
                    ("released", "Released"),
                ],
                default="payment_pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="prescription",
            name="released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prescription",
            name="released_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="released_prescriptions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            release_existing_prescriptions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
