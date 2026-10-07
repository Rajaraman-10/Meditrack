from .models import Notification


def create_notification(*, recipient, title, message, category, target_url=""):
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        category=category,
        target_url=target_url,
    )
