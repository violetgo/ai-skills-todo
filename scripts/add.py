#!/usr/bin/env python3
"""Add a new task to active.json.

Usage:
  python3 add.py '<task_json>'

The task_json must include at minimum: title, description, type, deadline,
estimated_hours, scores (benefit, effort, confidence), and optionally tags,
milestones (for long_term tasks).

The script will:
- Auto-generate id
- Auto-calculate urgency from deadline
- Auto-assign quadrant
- Calculate priority_score
- Append to active.json
"""

import json
import os
import sys
from datetime import datetime, date

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calculate_days_remaining(deadline_str):
    deadline = date.fromisoformat(deadline_str)
    return (deadline - date.today()).days


def calculate_urgency(days_remaining, config):
    urgency = 5
    levels = sorted(config["dynamic_urgency"]["levels"], key=lambda x: x["days_lte"])
    for level in levels:
        if days_remaining <= level["days_lte"]:
            urgency = max(urgency, level["urgency_min"])
    return urgency


def assign_quadrant(days_remaining, benefit, config):
    urgent_days = config["quadrant"]["urgent_days"]
    important_threshold = config["quadrant"]["important_threshold"]

    is_urgent = days_remaining <= urgent_days
    is_important = benefit >= important_threshold

    if is_important and is_urgent:
        return "important_urgent"
    elif is_important and not is_urgent:
        return "important_not_urgent"
    elif not is_important and is_urgent:
        return "not_important_urgent"
    else:
        return "not_important_not_urgent"


def calculate_priority_score(scores, config):
    w = config["weights"]
    s = scores
    score = (
        s["benefit"] * w["benefit"]
        + s["urgency"] * w["urgency"]
        + (10 - s["effort"]) * w["effort"]
        + s["confidence"] * w["confidence"]
    )
    return round(score, 2)


def generate_id(active_data):
    today_str = date.today().strftime("%Y%m%d")
    existing_today = [
        t["id"] for t in active_data["tasks"] if t["id"].startswith(today_str)
    ]
    seq = len(existing_today) + 1
    return f"{today_str}-{seq:03d}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: add.py '<task_json>'"}))
        sys.exit(1)

    try:
        task_input = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
        sys.exit(1)

    config = load_json(CONFIG_FILE)
    active = load_json(ACTIVE_FILE)

    # Calculate derived fields
    days_remaining = calculate_days_remaining(task_input["deadline"])
    urgency = calculate_urgency(days_remaining, config)

    scores = {
        "benefit": task_input["scores"]["benefit"],
        "urgency": urgency,
        "effort": task_input["scores"]["effort"],
        "confidence": task_input["scores"]["confidence"],
    }

    quadrant = task_input.get("quadrant") or assign_quadrant(
        days_remaining, scores["benefit"], config
    )

    priority_score = calculate_priority_score(scores, config)

    task_type = task_input.get("type", "one_off")

    task = {
        "id": generate_id(active),
        "title": task_input["title"],
        "description": task_input.get("description", ""),
        "type": task_type,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "deadline": task_input["deadline"],
        "quadrant": quadrant,
        "scores": scores,
        "priority_score": priority_score,
        "status": "pending",
        "completed_at": None,
        "tags": task_input.get("tags", []),
        "context": task_input.get("context", ""),
        "depends_on": task_input.get("depends_on", []),
        "start_date": task_input.get("start_date", None),
    }

    # one_off tasks have estimated_hours at task level
    if task_type == "one_off":
        task["estimated_hours"] = task_input.get("estimated_hours", 0)
        task["actual_hours"] = None

    # Long-term tasks: no task-level estimated_hours, hours live on milestones
    if task_type == "long_term":
        task["milestones"] = task_input.get("milestones", [])
        task["progress_notes"] = []
        task["actual_hours"] = None

    active["tasks"].append(task)
    save_json(ACTIVE_FILE, active)

    result = {
        "status": "ok",
        "task": task,
        "active_count": len(active["tasks"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
