from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from .models import Task


@extend_schema_field(OpenApiTypes.FLOAT)
class EpochDateTimeField(serializers.Field):
    def to_representation(self, value):
        if value is None:
            return None
        return value.timestamp()

    def to_internal_value(self, data):
        if data in ("", None):
            return None
        try:
            from datetime import datetime, timezone

            return datetime.fromtimestamp(float(data), tz=timezone.utc)
        except (TypeError, ValueError, OSError) as exc:
            raise serializers.ValidationError("Expected epoch seconds.") from exc


class TaskSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="id")
    created_at = EpochDateTimeField()
    updated_at = EpochDateTimeField()
    completed_at = EpochDateTimeField(required=False, allow_null=True)
    deadline_at = EpochDateTimeField(required=False, allow_null=True)
    planned_start_at = EpochDateTimeField(required=False, allow_null=True)
    planned_end_at = EpochDateTimeField(required=False, allow_null=True)
    timer_started_at = EpochDateTimeField(required=False, allow_null=True)
    timer_ends_at = EpochDateTimeField(required=False, allow_null=True)
    client_updated_at = EpochDateTimeField(required=False, allow_null=True)
    synced_at = EpochDateTimeField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "task_id",
            "text",
            "created_at",
            "updated_at",
            "completed",
            "completed_at",
            "position",
            "color_tags",
            "deadline_at",
            "planned_start_at",
            "planned_end_at",
            "timer_started_at",
            "timer_ends_at",
            "timer_duration_seconds",
            "timer_paused_remaining_seconds",
            "client_updated_at",
            "synced_at",
        ]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        self._apply_completed_at_transition(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._apply_completed_at_transition(validated_data, instance)
        return super().update(instance, validated_data)

    def _apply_completed_at_transition(self, validated_data, instance=None):
        if "completed" not in validated_data:
            return

        completed = bool(validated_data["completed"])
        was_completed = bool(instance.completed) if instance is not None else False
        if completed and not was_completed and not validated_data.get("completed_at"):
            validated_data["completed_at"] = validated_data.get("client_updated_at") or validated_data.get("updated_at")
        elif not completed:
            validated_data["completed_at"] = None


class ReorderSerializer(serializers.Serializer):
    tasks = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
