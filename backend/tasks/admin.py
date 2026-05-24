from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Task


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ["text", "user", "position", "updated_at", "deadline_at"]
    list_filter = ["user", "completed", "deadline_at"]
    search_fields = ["text", "user__username"]
    readonly_fields = ["synced_at"]
