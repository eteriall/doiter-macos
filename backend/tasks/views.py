import json

from django.db import transaction
from rest_framework import decorators, status, viewsets
from rest_framework.response import Response

from .models import Task
from .serializers import ReorderSerializer, TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    lookup_value_regex = "[0-9A-Fa-f-]{36}"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        before = self._task_debug_snapshot(serializer.instance)
        task = serializer.save()
        self._print_task_update_debug(task, before)

    def _task_debug_snapshot(self, task):
        return {
            field.name: getattr(task, field.name)
            for field in task._meta.fields
            if field.name not in {"synced_at", "user"}
        }

    def _print_task_update_debug(self, task, before):
        after = self._task_debug_snapshot(task)
        changed = {
            key: {
                "before": before.get(key),
                "after": after.get(key),
            }
            for key in after.keys()
            if before.get(key) != after.get(key)
        }
        meta = self.request.META
        device = {
            "id": meta.get("HTTP_X_DOITER_DEVICE_ID") or "unknown",
            "name": meta.get("HTTP_X_DOITER_DEVICE_NAME") or meta.get("HTTP_USER_AGENT") or "unknown",
            "platform": meta.get("HTTP_X_DOITER_DEVICE_PLATFORM") or "unknown",
        }
        message = {
            "event": "task_updated",
            "task_id": str(task.id),
            "user": getattr(self.request.user, "username", None),
            "method": self.request.method,
            "device": device,
            "changed": changed,
        }
        print(f"[doiter-debug] {json.dumps(message, default=str, sort_keys=True)}", flush=True)

    def create(self, request, *args, **kwargs):
        """Create or update by client-provided task_id for idempotent sync."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = serializer.validated_data.get("id")

        existing = self.get_queryset().filter(id=task_id).first() if task_id else None
        if existing:
            update_serializer = self.get_serializer(existing, data=request.data, partial=True)
            update_serializer.is_valid(raise_exception=True)
            self.perform_update(update_serializer)
            return Response(update_serializer.data, status=status.HTTP_200_OK)

        if task_id and Task.objects.filter(id=task_id).exclude(user=request.user).exists():
            return Response(
                {"detail": "A task with this id belongs to another user."},
                status=status.HTTP_409_CONFLICT,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @decorators.action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        by_id = {str(task.id): task for task in self.get_queryset()}

        with transaction.atomic():
            for item in serializer.validated_data["tasks"]:
                task_id = str(item.get("task_id") or item.get("id") or "")
                if task_id not in by_id or "position" not in item:
                    continue
                before = self._task_debug_snapshot(by_id[task_id])
                by_id[task_id].position = int(item["position"])
                by_id[task_id].save(update_fields=["position", "synced_at"])
                self._print_task_update_debug(by_id[task_id], before)

        return Response(self.get_serializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)
