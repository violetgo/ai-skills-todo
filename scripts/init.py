#!/usr/bin/env python3
"""Initialize TODO data directory and files."""

import json
import os
import sys

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

DEFAULT_CONFIG = {
    "weights": {
        "benefit": 0.35,
        "urgency": 0.3,
        "effort": 0.15,
        "confidence": 0.2,
    },
    "quadrant": {
        "urgent_days": 14,
        "important_threshold": 7,
    },
    "dynamic_urgency": {
        "levels": [
            {"days_lte": 3, "urgency_min": 10},
            {"days_lte": 7, "urgency_min": 8},
        ]
    },
    "momentum_bonus_max": 2.0,
    "recommend_count": 5,
}


def init():
    created = []
    existed = []

    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
        created.append(DATA_DIR)
    else:
        existed.append(DATA_DIR)

    if not os.path.isdir(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        created.append(ARCHIVE_DIR)
    else:
        existed.append(ARCHIVE_DIR)

    if not os.path.isfile(ACTIVE_FILE):
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": []}, f, ensure_ascii=False, indent=2)
        created.append(ACTIVE_FILE)
    else:
        existed.append(ACTIVE_FILE)

    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        created.append(CONFIG_FILE)
    else:
        existed.append(CONFIG_FILE)

    result = {"status": "ok", "created": created, "existed": existed}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    init()
