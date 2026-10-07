from django.db import models


class Medicine(models.Model):
    source_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=180)
    generic_name = models.CharField(max_length=180, blank=True)
    strength = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=80, blank=True)
    route = models.CharField(max_length=80, blank=True)
    manufacturer = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name", "strength")
        constraints = [
            models.UniqueConstraint(
                fields=("name", "strength", "dosage_form"),
                name="unique_medicine_product",
            ),
        ]
        indexes = [
            models.Index(fields=("name", "strength")),
            models.Index(fields=("generic_name",)),
        ]

    def __str__(self):
        return f"{self.name} {self.strength}".strip()


class Prescription(models.Model):
    class Status(models.TextChoices):
        PAYMENT_PENDING = "payment_pending", "Payment pending"
        RELEASED = "released", "Released"

    consultation = models.ForeignKey(
        "consultations.Consultation",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAYMENT_PENDING,
    )
    released_at = models.DateTimeField(blank=True, null=True)
    released_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="released_prescriptions",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class PrescriptionItem(models.Model):
    class FoodTiming(models.TextChoices):
        BEFORE_FOOD = "before_food", "Before food"
        AFTER_FOOD = "after_food", "After food"
        WITH_FOOD = "with_food", "With food"
        ANY = "any", "Any time"

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items",
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="prescription_items",
        null=True,
        blank=True,
    )
    medication_name = models.CharField(max_length=180)
    strength = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=180)
    route = models.CharField(max_length=80, blank=True)
    frequency = models.CharField(max_length=180)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    food_timing = models.CharField(
        max_length=16,
        choices=FoodTiming.choices,
        blank=True,
    )

    class Meta:
        ordering = ("id",)
