import uuid

from django.conf import settings
from django.db import models


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    text = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.IntegerField(default=0)
    color_tags = models.JSONField(default=list, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    planned_start_at = models.DateTimeField(null=True, blank=True)
    planned_end_at = models.DateTimeField(null=True, blank=True)
    timer_started_at = models.DateTimeField(null=True, blank=True)
    timer_ends_at = models.DateTimeField(null=True, blank=True)
    timer_duration_seconds = models.IntegerField(null=True, blank=True)
    timer_paused_remaining_seconds = models.IntegerField(null=True, blank=True)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-position", "-created_at"]
        indexes = [
            models.Index(fields=["user", "position"]),
            models.Index(fields=["user", "updated_at"]),
        ]

    def __str__(self):
        return self.text
