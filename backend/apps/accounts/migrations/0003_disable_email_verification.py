from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_email_verified"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="email_verified",
        ),
    ]
