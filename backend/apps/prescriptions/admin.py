from django.contrib import admin

from .models import Medicine, Prescription, PrescriptionItem


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "generic_name", "strength", "dosage_form", "route", "is_active")
    list_filter = ("is_active", "dosage_form")
    search_fields = ("name", "generic_name", "strength", "manufacturer")


admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
