from django.db import migrations


def keep_task_titles_only(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    for task in Task.objects.all().only("id", "text"):
        title = (task.text or "").splitlines()[0].strip()
        if title != task.text:
            task.text = title
            task.save(update_fields=["text"])


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0002_task_completed_at"),
    ]

    operations = [
        migrations.RunPython(keep_task_titles_only, migrations.RunPython.noop),
    ]
