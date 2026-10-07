from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "category", "target_url", "created_at", "read_at")
        read_only_fields = ("id", "title", "message", "category", "target_url", "created_at", "read_at")


class NotificationReadSerializer(serializers.Serializer):
    is_read = serializers.BooleanField()
