"""Shared definitions for color tags applied to tasks."""

COLOR_TAGS = [
    {
        "key": "red",
        "name": "Red",
        "hex": "#FF383C",
        "rgb": (255, 56, 60),
        "key_code": 18,  # Cmd+1
    },
    {
        "key": "orange",
        "name": "Orange",
        "hex": "#FF8D28",
        "rgb": (255, 141, 40),
        "key_code": 19,  # Cmd+2
    },
    {
        "key": "yellow",
        "name": "Yellow",
        "hex": "#FFCC00",
        "rgb": (255, 204, 0),
        "key_code": 20,  # Cmd+3
    },
    {
        "key": "green",
        "name": "Green",
        "hex": "#34C759",
        "rgb": (52, 199, 89),
        "key_code": 21,  # Cmd+4
    },
    {
        "key": "blue",
        "name": "Blue",
        "hex": "#0088FF",
        "rgb": (0, 136, 255),
        "key_code": 23,  # Cmd+5
    },
    {
        "key": "purple",
        "name": "Purple",
        "hex": "#CB30E0",
        "rgb": (203, 48, 224),
        "key_code": 22,  # Cmd+6
    },
    {
        "key": "gray",
        "name": "Gray",
        "hex": "#8E8E93",
        "rgb": (142, 142, 147),
        "key_code": 26,  # Cmd+7
    },
]

COLOR_TAG_KEY_ORDER = [tag["key"] for tag in COLOR_TAGS]
COLOR_TAG_KEYCODE_MAP = {tag["key_code"]: tag["key"] for tag in COLOR_TAGS}
COLOR_TAG_NAME_MAP = {tag["key"]: tag["name"] for tag in COLOR_TAGS}
COLOR_TAG_RGB_MAP = {tag["key"]: tag["rgb"] for tag in COLOR_TAGS}

ACCENT_RGB_MAP = {
    "timer": (0, 136, 255),       # Blue
    "timer_done": (255, 56, 60),  # Red
    "paused": (255, 141, 40),     # Orange
    "planned": (0, 200, 179),     # Mint
    "active": (52, 199, 89),      # Green
    "deadline": (203, 48, 224),   # Purple
    "overdue": (255, 56, 60),     # Red
}
