from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=24, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.code:
            base_code = slugify(self.name).upper().replace("-", "_")[:24] or "DEPT"
            candidate = base_code
            suffix = 2
            departments = Department.objects.exclude(pk=self.pk)
            while departments.filter(code=candidate).exists():
                candidate = f"{base_code[:20]}_{suffix}"
                suffix += 1
            self.code = candidate
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="doctor_profile",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="doctors",
    )
    license_number = models.CharField(max_length=80, unique=True)
    specialization = models.CharField(max_length=160)
    phone = models.CharField(max_length=32, blank=True)
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    slot_duration_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(240)],
    )
    bio = models.TextField(blank=True)
    is_accepting_appointments = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name", "user__email")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(slot_duration_minutes__gte=5)
                & models.Q(slot_duration_minutes__lte=240),
                name="doctor_slot_duration_range",
            ),
            models.CheckConstraint(
                condition=models.Q(consultation_fee__gte=0),
                name="doctor_consultation_fee_nonnegative",
            ),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.email}"


class DoctorAvailability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="availability",
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("weekday", "start_time")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0) & models.Q(weekday__lte=6),
                name="doctor_availability_weekday_range",
            ),
            models.UniqueConstraint(
                fields=("doctor", "weekday", "start_time"),
                name="unique_doctor_weekday_start",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="doctor_availability_end_after_start",
            ),
        ]
        indexes = [models.Index(fields=("doctor", "weekday", "is_active"))]

    def __str__(self):
        return f"{self.doctor} · {self.get_weekday_display()}"


class ScheduleException(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="schedule_exceptions",
    )
    date = models.DateField()
    is_closed = models.BooleanField(default=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "date"),
                name="unique_doctor_schedule_exception_date",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_closed=True)
                    | (
                        models.Q(start_time__isnull=False)
                        & models.Q(end_time__isnull=False)
                        & models.Q(end_time__gt=models.F("start_time"))
                    )
                ),
                name="open_exception_requires_valid_hours",
            ),
        ]
        indexes = [models.Index(fields=("doctor", "date"))]

    def __str__(self):
        return f"{self.doctor} · {self.date}"
