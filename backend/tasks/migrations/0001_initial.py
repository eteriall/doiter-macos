# Generated for doiter backend bootstrap.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
                ("completed", models.BooleanField(default=False)),
                ("position", models.IntegerField(default=0)),
                ("color_tags", models.JSONField(blank=True, default=list)),
                ("deadline_at", models.DateTimeField(blank=True, null=True)),
                ("planned_start_at", models.DateTimeField(blank=True, null=True)),
                ("planned_end_at", models.DateTimeField(blank=True, null=True)),
                ("timer_started_at", models.DateTimeField(blank=True, null=True)),
                ("timer_ends_at", models.DateTimeField(blank=True, null=True)),
                ("timer_duration_seconds", models.IntegerField(blank=True, null=True)),
                ("timer_paused_remaining_seconds", models.IntegerField(blank=True, null=True)),
                ("client_updated_at", models.DateTimeField(blank=True, null=True)),
                ("synced_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-position", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "position"], name="tasks_task_user_id_c506ea_idx"),
                    models.Index(fields=["user", "updated_at"], name="tasks_task_user_id_66b666_idx"),
                ],
            },
        ),
    ]
