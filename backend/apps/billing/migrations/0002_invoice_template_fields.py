from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="currency",
            field=models.CharField(default="INR", max_length=3),
        ),
        migrations.AddField(
            model_name="invoice",
            name="discount_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("upi", "UPI"),
                    ("cash", "Cash"),
                    ("card", "Card"),
                    ("bank_transfer", "Bank transfer"),
                    ("other", "Other"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="transaction_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
