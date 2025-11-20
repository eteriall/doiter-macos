"""Shared definitions for color tags applied to tasks."""

COLOR_TAGS = [
    {
        "key": "red",
        "emoji": "🔴",
        "name": "Red",
        "hex": "#FF3B30",
        "key_code": 18,  # Cmd+1
    },
    {
        "key": "orange",
        "emoji": "🟠",
        "name": "Orange",
        "hex": "#FF9500",
        "key_code": 19,  # Cmd+2
    },
    {
        "key": "yellow",
        "emoji": "🟡",
        "name": "Yellow",
        "hex": "#FFCC00",
        "key_code": 20,  # Cmd+3
    },
    {
        "key": "green",
        "emoji": "🟢",
        "name": "Green",
        "hex": "#34C759",
        "key_code": 21,  # Cmd+4
    },
    {
        "key": "blue",
        "emoji": "🔵",
        "name": "Blue",
        "hex": "#007AFF",
        "key_code": 23,  # Cmd+5
    },
    {
        "key": "purple",
        "emoji": "🟣",
        "name": "Purple",
        "hex": "#AF52DE",
        "key_code": 22,  # Cmd+6
    },
    {
        "key": "gray",
        "emoji": "⚪️",
        "name": "Gray",
        "hex": "#8E8E93",
        "key_code": 26,  # Cmd+7
    },
]

COLOR_TAG_KEY_ORDER = [tag["key"] for tag in COLOR_TAGS]
COLOR_TAG_EMOJI_MAP = {tag["key"]: tag["emoji"] for tag in COLOR_TAGS}
COLOR_TAG_KEYCODE_MAP = {tag["key_code"]: tag["key"] for tag in COLOR_TAGS}
