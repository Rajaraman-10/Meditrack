from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_disable_email_verification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("doctor", "Doctor"),
                    ("receptionist", "Receptionist"),
                    ("billing", "Billing"),
                    ("patient", "Patient"),
                ],
                default="patient",
                max_length=16,
            ),
        ),
    ]
