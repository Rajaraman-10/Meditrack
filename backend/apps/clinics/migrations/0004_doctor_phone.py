from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinics", "0003_department_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="doctorprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
