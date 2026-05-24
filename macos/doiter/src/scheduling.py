import re
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple


class ScheduleParseError(ValueError):
    """Raised when a schedule command value cannot be parsed."""


def _base_now(now: Optional[datetime] = None) -> datetime:
    return now or datetime.now()


def _parse_date(value: str, now: datetime) -> date:
    value = value.strip().lower()
    if value == "today":
        return now.date()
    if value == "tomorrow":
        return now.date() + timedelta(days=1)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ScheduleParseError("Use today, tomorrow, or YYYY-MM-DD") from exc


def _parse_time(value: str) -> Tuple[int, int]:
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", value.strip())
    if not match:
        raise ScheduleParseError("Use time like 14:30")
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    if hour > 23 or minute > 59:
        raise ScheduleParseError("Time must be 00:00-23:59")
    return hour, minute


def parse_deadline(value: str, now: Optional[datetime] = None) -> float:
    """Parse deadline input into local epoch seconds."""
    current = _base_now(now)
    raw = value.strip()
    if not raw:
        raise ScheduleParseError("Enter a deadline")

    parts = raw.split()
    if len(parts) == 1:
        token = parts[0].lower()
        if token in ("today", "tomorrow") or re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
            dt = datetime.combine(_parse_date(token, current), datetime.min.time())
        else:
            hour, minute = _parse_time(token)
            dt = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dt <= current:
                dt += timedelta(days=1)
    elif len(parts) == 2:
        due_date = _parse_date(parts[0], current)
        hour, minute = _parse_time(parts[1])
        dt = datetime.combine(due_date, datetime.min.time()).replace(hour=hour, minute=minute)
    else:
        raise ScheduleParseError("Use date, time, or date time")

    return dt.timestamp()


def parse_planned_slot(value: str, now: Optional[datetime] = None) -> Tuple[float, float]:
    """Parse planned slot input into start/end local epoch seconds."""
    current = _base_now(now)
    raw = value.strip()
    if not raw or "-" not in raw:
        raise ScheduleParseError("Use slot like 14:00-15:30")

    prefix = ""
    slot = raw
    parts = raw.split(maxsplit=1)
    if len(parts) == 2 and "-" in parts[1]:
        prefix, slot = parts

    start_raw, end_raw = [part.strip() for part in slot.split("-", 1)]
    slot_date = _parse_date(prefix, current) if prefix else current.date()
    start_hour, start_minute = _parse_time(start_raw)
    end_hour, end_minute = _parse_time(end_raw)
    start_dt = datetime.combine(slot_date, datetime.min.time()).replace(
        hour=start_hour,
        minute=start_minute,
    )
    end_dt = datetime.combine(slot_date, datetime.min.time()).replace(
        hour=end_hour,
        minute=end_minute,
    )
    if end_dt <= start_dt:
        raise ScheduleParseError("Slot end must be after start")
    return start_dt.timestamp(), end_dt.timestamp()


def parse_duration(value: str) -> int:
    """Parse timer duration into seconds."""
    raw = value.strip().lower()
    if not raw:
        raise ScheduleParseError("Enter a timer duration")

    if re.fullmatch(r"\d+", raw):
        seconds = int(raw) * 60
        if seconds < 60:
            raise ScheduleParseError("Timer must be at least 1 minute")
        return seconds

    matches = re.findall(r"(\d+)\s*([hm])", raw)
    if not matches or "".join(f"{amount}{unit}" for amount, unit in matches) != raw.replace(" ", ""):
        raise ScheduleParseError("Use duration like 25, 25m, or 1h 30m")

    seconds = 0
    for amount, unit in matches:
        value_int = int(amount)
        seconds += value_int * (3600 if unit == "h" else 60)
    if seconds < 60:
        raise ScheduleParseError("Timer must be at least 1 minute")
    return seconds


def is_active_task(task: Dict, now_ts: Optional[float] = None) -> bool:
    now_value = now_ts if now_ts is not None else time.time()
    timer_ends = task.get("timer_ends_at")
    if timer_ends and timer_ends > now_value:
        return True
    start = task.get("planned_start_at")
    end = task.get("planned_end_at")
    return bool(start and end and start <= now_value < end)


def compact_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes:02d}m"


def format_task_badge_parts(task: Dict, now_ts: Optional[float] = None) -> List[Tuple[str, str]]:
    """Return schedule badges as (accent_key, text) pairs."""
    now_value = now_ts if now_ts is not None else time.time()
    badges = []
    timer_ends = task.get("timer_ends_at")
    paused_remaining = task.get("timer_paused_remaining_seconds")
    if timer_ends:
        if timer_ends > now_value:
            badges.append(("timer", compact_duration(timer_ends - now_value)))
        else:
            badges.append(("timer_done", "done"))
    elif paused_remaining:
        badges.append(("paused", compact_duration(paused_remaining)))

    start = task.get("planned_start_at")
    end = task.get("planned_end_at")
    if start and end:
        if start <= now_value < end:
            badges.append(("active", compact_duration(end - now_value)))
        else:
            start_dt = datetime.fromtimestamp(start)
            end_dt = datetime.fromtimestamp(end)
            if start_dt.date() == datetime.fromtimestamp(now_value).date():
                badges.append(("planned", f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"))
            else:
                badges.append(("planned", f"{start_dt.strftime('%a %H:%M')}-{end_dt.strftime('%H:%M')}"))

    deadline = task.get("deadline_at")
    if deadline:
        if deadline <= now_value:
            badges.append(("overdue", datetime.fromtimestamp(deadline).strftime('%a %H:%M')))
        else:
            badges.append(("deadline", datetime.fromtimestamp(deadline).strftime('%a %H:%M')))

    return badges


def format_task_badge(task: Dict, now_ts: Optional[float] = None) -> str:
    badges = [text for _, text in format_task_badge_parts(task, now_ts)]
    return " ".join(badges)
