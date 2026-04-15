#!/usr/bin/env python3
"""Recommend top-priority tasks from active.json.

Usage:
  python3 recommend.py [count]

Reads active tasks, recalculates priorities with dynamic urgency and momentum
bonus, sorts by quadrant then score, and outputs the top N as JSON.
"""

import json
import os
import sys
from datetime import date

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

QUADRANT_RANK = {
    "important_urgent": 1,
    "important_not_urgent": 2,
    "not_important_urgent": 3,
    "not_important_not_urgent": 4,
}

QUADRANT_LABEL = {
    "important_urgent": "Important & Urgent",
    "important_not_urgent": "Important & Not Urgent",
    "not_important_urgent": "Urgent & Not Important",
    "not_important_not_urgent": "Neither",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def days_remaining(deadline_str):
    return (date.fromisoformat(deadline_str) - date.today()).days


def effective_deadline(task):
    """For long-term tasks, use the earlier of task deadline and next milestone deadline."""
    dl = task["deadline"]
    if task.get("type") == "long_term" and task.get("milestones"):
        for m in task["milestones"]:
            if m.get("completed_at") is None and m.get("deadline"):
                m_dl = m["deadline"]
                if m_dl < dl:
                    dl = m_dl
                break  # milestones are ordered
    return dl


def apply_dynamic_urgency(base_urgency, days_left, config):
    urgency = base_urgency
    levels = sorted(config["dynamic_urgency"]["levels"], key=lambda x: x["days_lte"])
    for level in levels:
        if days_left <= level["days_lte"]:
            urgency = max(urgency, level["urgency_min"])
    return urgency


def calculate_priority(scores, config):
    w = config["weights"]
    return round(
        scores["benefit"] * w["benefit"]
        + scores["urgency"] * w["urgency"]
        + (10 - scores["effort"]) * w["effort"]
        + scores["confidence"] * w["confidence"],
        2,
    )


def momentum_bonus(task, config):
    if task.get("type") != "long_term" or not task.get("milestones"):
        return 0.0
    total = len(task["milestones"])
    done = sum(1 for m in task["milestones"] if m.get("completed_at"))
    if total == 0:
        return 0.0
    return round((done / total) * config["momentum_bonus_max"], 2)


def current_milestone(task):
    """Return the first incomplete milestone, or None."""
    if task.get("type") != "long_term" or not task.get("milestones"):
        return None
    for m in task["milestones"]:
        if m.get("completed_at") is None:
            return m
    return None


def main():
    config = load_json(CONFIG_FILE)
    active = load_json(ACTIVE_FILE)

    count = int(sys.argv[1]) if len(sys.argv) > 1 else config.get("recommend_count", 5)

    tasks = active["tasks"]
    if not tasks:
        print(json.dumps({"status": "ok", "tasks": [], "overdue": [], "not_started": [], "total_active": 0}))
        return

    today = date.today()
    scored = []
    overdue = []
    blocked = []
    not_started = []

    # Build set of completed task IDs (check archive too) and active task IDs
    active_ids = {t["id"] for t in tasks}
    completed_ids = set()
    archive_dir = os.path.join(DATA_DIR, "archive")
    if os.path.isdir(archive_dir):
        for fn in os.listdir(archive_dir):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(archive_dir, fn), "r") as f:
                        for t in json.load(f).get("tasks", []):
                            completed_ids.add(t["id"])
                except (json.JSONDecodeError, KeyError):
                    pass

    for task in tasks:
        # Check start_date — not yet actionable
        task_start = task.get("start_date")
        if task_start and date.fromisoformat(task_start) > today:
            days_until = (date.fromisoformat(task_start) - today).days
            not_started.append({
                "id": task["id"],
                "title": task["title"],
                "start_date": task_start,
                "days_until_start": days_until,
            })
            continue

        dl = effective_deadline(task)
        days_left = days_remaining(dl)

        # Check overdue
        if days_left < 0:
            overdue.append({
                "id": task["id"],
                "title": task["title"],
                "deadline": task["deadline"],
                "days_overdue": abs(days_left),
            })

        # Dynamic urgency
        adjusted_urgency = apply_dynamic_urgency(
            task["scores"].get("urgency", 5), days_left, config
        )
        adjusted_scores = dict(task["scores"])
        adjusted_scores["urgency"] = adjusted_urgency

        # Priority
        base_score = calculate_priority(adjusted_scores, config)
        bonus = momentum_bonus(task, config)
        final_score = round(base_score + bonus, 2)

        cm = current_milestone(task)

        # Check dependencies
        deps = task.get("depends_on", [])
        unmet = [d for d in deps if d not in completed_ids]
        is_blocked = len(unmet) > 0

        if is_blocked:
            # Find titles of blocking tasks
            blocking_titles = []
            for uid in unmet:
                for t in tasks:
                    if t["id"] == uid:
                        blocking_titles.append(t["title"])
                        break
                else:
                    blocking_titles.append(uid)
            blocked.append({
                "id": task["id"],
                "title": task["title"],
                "blocked_by": [{"id": uid, "title": bt} for uid, bt in zip(unmet, blocking_titles)],
            })
            continue  # skip blocked tasks from main ranking

        scored.append({
            "id": task["id"],
            "title": task["title"],
            "type": task.get("type", "one_off"),
            "quadrant": task["quadrant"],
            "quadrant_label": QUADRANT_LABEL.get(task["quadrant"], task["quadrant"]),
            "quadrant_rank": QUADRANT_RANK.get(task["quadrant"], 99),
            "priority_score": final_score,
            "deadline": task["deadline"],
            "days_remaining": days_left,
            "current_milestone": cm,
            "milestones_done": sum(1 for m in task.get("milestones", []) if m.get("completed_at")),
            "milestones_total": len(task.get("milestones", [])),
            "momentum_bonus": bonus,
        })

    # Sort: quadrant rank asc, then priority_score desc
    scored.sort(key=lambda x: (x["quadrant_rank"], -x["priority_score"]))

    result = {
        "status": "ok",
        "tasks": scored[:count],
        "overdue": overdue,
        "blocked": blocked,
        "not_started": not_started,
        "total_active": len(tasks),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
