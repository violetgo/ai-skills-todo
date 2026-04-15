#!/usr/bin/env python3
"""Review completed tasks over a date range.

Usage:
  python3 review.py <start_date> [end_date]

  start_date: YYYY-MM-DD
  end_date:   YYYY-MM-DD (defaults to today)

Outputs:
- Completed tasks from archive files in the range
- Long-term task milestone/progress activity from active.json
- Summary statistics
"""

import json
import os
import sys
from datetime import date

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

QUADRANT_LABEL = {
    "important_urgent": "Important & Urgent",
    "important_not_urgent": "Important & Not Urgent",
    "not_important_urgent": "Urgent & Not Important",
    "not_important_not_urgent": "Neither",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: review.py <start_date> [end_date]",
        }))
        sys.exit(1)

    start_date = date.fromisoformat(sys.argv[1])
    end_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    # Collect completed tasks from archive
    completed_tasks = []
    if os.path.isdir(ARCHIVE_DIR):
        for filename in sorted(os.listdir(ARCHIVE_DIR)):
            if not filename.endswith(".json"):
                continue
            file_date_str = filename.replace(".json", "")
            try:
                file_date = date.fromisoformat(file_date_str)
            except ValueError:
                continue
            if start_date <= file_date <= end_date:
                archive = load_json(os.path.join(ARCHIVE_DIR, filename))
                for task in archive.get("tasks", []):
                    completed_tasks.append({
                        "date": file_date_str,
                        "id": task["id"],
                        "title": task["title"],
                        "type": task.get("type", "one_off"),
                        "quadrant": task.get("quadrant", ""),
                        "quadrant_label": QUADRANT_LABEL.get(task.get("quadrant", ""), ""),
                        "estimated_hours": task.get("estimated_hours", 0),
                        "context": task.get("context", ""),
                    })

    # Collect long-term task activity from active tasks
    long_term_activity = []
    if os.path.isfile(ACTIVE_FILE):
        active = load_json(ACTIVE_FILE)
        for task in active.get("tasks", []):
            if task.get("type") != "long_term":
                continue
            activity = {"task_id": task["id"], "title": task["title"], "events": []}

            for m in task.get("milestones", []):
                if m.get("completed_at"):
                    m_date_str = m["completed_at"][:10]
                    try:
                        m_date = date.fromisoformat(m_date_str)
                        if start_date <= m_date <= end_date:
                            activity["events"].append({
                                "date": m_date_str,
                                "type": "milestone_completed",
                                "title": m["title"],
                            })
                    except ValueError:
                        pass

            for note in task.get("progress_notes", []):
                try:
                    n_date = date.fromisoformat(note["date"])
                    if start_date <= n_date <= end_date:
                        activity["events"].append({
                            "date": note["date"],
                            "type": "progress_note",
                            "note": note["note"],
                        })
                except ValueError:
                    pass

            if activity["events"]:
                activity["events"].sort(key=lambda x: x["date"])
                long_term_activity.append(activity)

    # Summary
    quadrant_counts = {}
    total_hours = 0
    for t in completed_tasks:
        q = t.get("quadrant_label", "Unknown")
        quadrant_counts[q] = quadrant_counts.get(q, 0) + 1
        total_hours += t.get("estimated_hours", 0)

    total_milestones = sum(
        sum(1 for e in a["events"] if e["type"] == "milestone_completed")
        for a in long_term_activity
    )

    result = {
        "status": "ok",
        "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "completed_tasks": completed_tasks,
        "long_term_activity": long_term_activity,
        "summary": {
            "total_completed": len(completed_tasks),
            "total_estimated_hours": total_hours,
            "by_quadrant": quadrant_counts,
            "milestones_completed": total_milestones,
            "long_term_tasks_advanced": len(long_term_activity),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
