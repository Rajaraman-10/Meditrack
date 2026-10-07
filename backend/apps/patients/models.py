from django.conf import settings
from django.db import models, transaction


class PatientNumberSequence(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_value = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = "patients_patient_number_sequence"


class PatientProfile(models.Model):
    patient_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_profile",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=32, blank=True)
    blood_group = models.CharField(max_length=3, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name", "user__email")

    def save(self, *args, **kwargs):
        if self.patient_number:
            return super().save(*args, **kwargs)

        using = kwargs.get("using") or self._state.db
        with transaction.atomic(using=using):
            sequence = (
                PatientNumberSequence.objects.using(using)
                .select_for_update()
                .get(pk=1)
            )
            sequence.last_value += 1
            sequence.save(using=using, update_fields=("last_value",))
            self.patient_number = f"MED-{sequence.last_value:06d}"
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_number} · {self.user.get_full_name() or self.user.email}"
