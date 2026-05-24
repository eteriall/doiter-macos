import os
import tempfile
import unittest
from datetime import datetime

from doiter.src.database import Database
from doiter.src.task_manager import TaskManager
from doiter.src.scheduling import (
    ScheduleParseError,
    format_task_badge,
    parse_deadline,
    parse_duration,
    parse_planned_slot,
)


class SchedulingParserTests(unittest.TestCase):
    def test_parse_time_only_deadline_uses_next_occurrence(self):
        now = datetime(2026, 5, 21, 16, 0)

        today = datetime.fromtimestamp(parse_deadline("17:00", now))
        tomorrow = datetime.fromtimestamp(parse_deadline("15:00", now))

        self.assertEqual(today.date(), now.date())
        self.assertEqual(today.hour, 17)
        self.assertEqual(tomorrow.date().day, 22)
        self.assertEqual(tomorrow.hour, 15)

    def test_parse_planned_slot_requires_end_after_start(self):
        now = datetime(2026, 5, 21, 10, 0)
        start, end = parse_planned_slot("14:00-15:30", now)

        self.assertEqual(datetime.fromtimestamp(start).hour, 14)
        self.assertEqual(datetime.fromtimestamp(end).minute, 30)
        with self.assertRaises(ScheduleParseError):
            parse_planned_slot("15:30-14:00", now)

    def test_parse_duration(self):
        self.assertEqual(parse_duration("25"), 1500)
        self.assertEqual(parse_duration("25m"), 1500)
        self.assertEqual(parse_duration("1h 30m"), 5400)
        with self.assertRaises(ScheduleParseError):
            parse_duration("30s")

    def test_badges_show_present_schedule_fields(self):
        now = datetime(2026, 5, 21, 10, 0).timestamp()
        badge = format_task_badge({
            "planned_start_at": datetime(2026, 5, 21, 14, 0).timestamp(),
            "planned_end_at": datetime(2026, 5, 21, 15, 30).timestamp(),
            "deadline_at": datetime(2026, 5, 22, 9, 0).timestamp(),
            "timer_paused_remaining_seconds": 1500,
        }, now)

        self.assertIn("25:00", badge)
        self.assertIn("14:00-15:30", badge)
        self.assertIn("Fri 09:00", badge)


class SchedulingDatabaseTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        os.remove(self.path)

    def test_schedule_fields_round_trip_and_undo_redo(self):
        task = self.db.add_task("task")

        self.db.update_schedule(task["task_id"], deadline_at=1234.0)
        self.assertEqual(self.db.get_task(task["task_id"])["deadline_at"], 1234.0)

        self.db.undo()
        self.assertIsNone(self.db.get_task(task["task_id"])["deadline_at"])

        self.db.redo()
        self.assertEqual(self.db.get_task(task["task_id"])["deadline_at"], 1234.0)

    def test_update_redo_restores_new_text(self):
        task = self.db.add_task("old")
        self.db.update_task(task["task_id"], "new")

        self.db.undo()
        self.assertEqual(self.db.get_task(task["task_id"])["text"], "old")

        self.db.redo()
        self.assertEqual(self.db.get_task(task["task_id"])["text"], "new")

    def test_redo_delete_does_not_clear_later_redo_items(self):
        first = self.db.add_task("first")
        second = self.db.add_task("second")
        self.db.delete_task(second["task_id"])
        self.db.update_task(first["task_id"], "first edited")

        self.db.undo()
        self.db.undo()
        self.db.redo()
        self.db.redo()

        self.assertEqual(self.db.get_task(first["task_id"])["text"], "first edited")
        self.assertIsNone(self.db.get_task(second["task_id"]))

    def test_paused_timer_field_round_trip(self):
        task = self.db.add_task("timer")
        self.db.update_schedule(
            task["task_id"],
            timer_started_at=None,
            timer_ends_at=None,
            timer_duration_seconds=1500,
            timer_paused_remaining_seconds=900,
        )

        stored = self.db.get_task(task["task_id"])
        self.assertEqual(stored["timer_duration_seconds"], 1500)
        self.assertEqual(stored["timer_paused_remaining_seconds"], 900)

    def test_swap_task_positions_and_undo_redo(self):
        first = self.db.add_task("first")
        second = self.db.add_task("second")

        self.assertEqual([task["text"] for task in self.db.get_all_tasks()], ["second", "first"])

        self.db.swap_task_positions(second["task_id"], first["task_id"])
        self.assertEqual([task["text"] for task in self.db.get_all_tasks()], ["first", "second"])

        self.db.undo()
        self.assertEqual([task["text"] for task in self.db.get_all_tasks()], ["second", "first"])

        self.db.redo()
        self.assertEqual([task["text"] for task in self.db.get_all_tasks()], ["first", "second"])

    def test_set_task_completed_and_undo_redo(self):
        task = self.db.add_task("task")

        self.db.set_task_completed(task["task_id"], True)
        self.assertEqual(self.db.get_task(task["task_id"])["completed"], 1)

        self.db.undo()
        self.assertEqual(self.db.get_task(task["task_id"])["completed"], 0)

        self.db.redo()
        self.assertEqual(self.db.get_task(task["task_id"])["completed"], 1)


class TaskManagerReorderTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.manager = TaskManager(self.path)

    def tearDown(self):
        self.manager.close()
        os.remove(self.path)

    def test_reorder_sync_and_undo_are_debounced_until_commit(self):
        first = self.manager.db.add_task("first")
        second = self.manager.db.add_task("second")
        third = self.manager.db.add_task("third")

        sync_triggers = []
        self.manager.set_sync_trigger(lambda: sync_triggers.append("sync"))

        self.assertEqual(
            [task["text"] for task in self.manager.get_tasks()],
            ["third", "second", "first"],
        )

        self.manager.swap_task_positions(third["task_id"], second["task_id"])
        self.manager.swap_task_positions(third["task_id"], first["task_id"])

        self.assertEqual(
            [task["text"] for task in self.manager.get_tasks()],
            ["second", "first", "third"],
        )
        self.assertEqual(self.manager.pending_sync_count(), 0)
        self.assertEqual(sync_triggers, [])

        self.manager.commit_pending_reorder()

        self.assertEqual(self.manager.pending_sync_count(), 3)
        self.assertEqual(sync_triggers, ["sync", "sync", "sync"])

        self.manager.undo()
        self.assertEqual(
            [task["text"] for task in self.manager.get_tasks()],
            ["third", "second", "first"],
        )


class TaskManagerCompletionTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.manager = TaskManager(self.path)

    def tearDown(self):
        self.manager.close()
        os.remove(self.path)

    def test_completion_and_reopen_queue_sync(self):
        task = self.manager.add_task("task")
        sync_triggers = []
        self.manager.set_sync_trigger(lambda: sync_triggers.append("sync"))

        completed = self.manager.mark_completed(task["task_id"])
        self.assertEqual(completed["completed"], 1)

        reopened = self.manager.reopen_task(task["task_id"])
        self.assertEqual(reopened["completed"], 0)

        payloads = [
            item["payload"]
            for item in self.manager.get_pending_sync_items()
            if item["task_id"] == task["task_id"] and item["payload"] is not None
        ]
        self.assertEqual(payloads[-2]["completed"], True)
        self.assertEqual(payloads[-1]["completed"], False)
        self.assertEqual(sync_triggers, ["sync", "sync"])


if __name__ == "__main__":
    unittest.main()
