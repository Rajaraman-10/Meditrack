from .models import AuditLog


def record_event(*, actor, action, instance, metadata=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=instance._meta.label_lower,
        object_id=str(instance.pk),
        metadata=metadata or {},
    )
