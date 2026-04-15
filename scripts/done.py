#!/usr/bin/env python3
"""Mark a task or milestone as complete.

Usage:
  python3 done.py --task <task_id>                      # Complete entire task
  python3 done.py --milestone <task_id> <milestone_idx> [--note "text"]  # Complete a milestone

When completing an entire task:
- Moves it from active.json to archive/YYYY-MM-DD.json

When completing a milestone:
- Updates the milestone's completed_at in active.json
- Adds a progress_note entry
"""

import json
import os
import sys
from datetime import datetime, date

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_task(active, task_id):
    for i, task in enumerate(active["tasks"]):
        if task["id"] == task_id:
            return i, task
    return -1, None


def complete_task(task_id, actual_hours=None):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)

    if idx == -1:
        print(json.dumps({"status": "error", "message": f"Task '{task_id}' not found"}))
        sys.exit(1)

    now = datetime.now().isoformat(timespec="seconds")
    task["status"] = "completed"
    task["completed_at"] = now
    if actual_hours is not None:
        task["actual_hours"] = actual_hours

    # Remove from active
    active["tasks"].pop(idx)
    save_json(ACTIVE_FILE, active)

    # Add to archive
    today_str = date.today().isoformat()
    archive_file = os.path.join(ARCHIVE_DIR, f"{today_str}.json")

    if os.path.isfile(archive_file):
        archive = load_json(archive_file)
    else:
        archive = {"tasks": []}

    archive["tasks"].append(task)
    save_json(archive_file, archive)

    result = {
        "status": "ok",
        "action": "task_completed",
        "task": task,
        "remaining_active": len(active["tasks"]),
        "archived_to": archive_file,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def complete_milestone(task_id, milestone_idx, note="", actual_hours=None):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)

    if idx == -1:
        print(json.dumps({"status": "error", "message": f"Task '{task_id}' not found"}))
        sys.exit(1)

    if task.get("type") != "long_term":
        print(json.dumps({"status": "error", "message": "Task is not long_term"}))
        sys.exit(1)

    milestones = task.get("milestones", [])
    if milestone_idx < 0 or milestone_idx >= len(milestones):
        print(json.dumps({
            "status": "error",
            "message": f"Milestone index {milestone_idx} out of range (0-{len(milestones)-1})",
        }))
        sys.exit(1)

    now = datetime.now().isoformat(timespec="seconds")
    today_str = date.today().isoformat()

    milestones[milestone_idx]["completed_at"] = now
    if note:
        milestones[milestone_idx]["note"] = note
    if actual_hours is not None:
        milestones[milestone_idx]["actual_hours"] = actual_hours

    # Add progress note
    if "progress_notes" not in task:
        task["progress_notes"] = []
    task["progress_notes"].append({
        "date": today_str,
        "note": note or f"Milestone \"{milestones[milestone_idx]['title']}\" completed",
    })

    # Update task status to in_progress if it was pending
    if task["status"] == "pending":
        task["status"] = "in_progress"

    save_json(ACTIVE_FILE, active)

    done_count = sum(1 for m in milestones if m.get("completed_at"))
    result = {
        "status": "ok",
        "action": "milestone_completed",
        "task_id": task_id,
        "task_title": task["title"],
        "milestone": milestones[milestone_idx],
        "milestones_done": done_count,
        "milestones_total": len(milestones),
        "remaining_active": len(active["tasks"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def list_tasks():
    """List all active tasks for matching."""
    active = load_json(ACTIVE_FILE)
    tasks = []
    for t in active["tasks"]:
        entry = {"id": t["id"], "title": t["title"], "type": t.get("type", "one_off")}
        if t.get("type") == "long_term" and t.get("milestones"):
            entry["milestones"] = [
                {
                    "index": i,
                    "title": m["title"],
                    "deadline": m.get("deadline"),
                    "completed": m.get("completed_at") is not None,
                }
                for i, m in enumerate(t["milestones"])
            ]
        tasks.append(entry)
    print(json.dumps({"status": "ok", "tasks": tasks}, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: done.py --task <id> | --milestone <id> <idx> [--note 'text'] | --list",
        }))
        sys.exit(1)

    def parse_optional(flag):
        if flag in sys.argv:
            idx = sys.argv.index(flag)
            if idx + 1 < len(sys.argv):
                return sys.argv[idx + 1]
        return None

    if sys.argv[1] == "--list":
        list_tasks()
    elif sys.argv[1] == "--task":
        if len(sys.argv) < 3:
            print(json.dumps({"status": "error", "message": "Missing task id"}))
            sys.exit(1)
        hours = parse_optional("--hours")
        complete_task(sys.argv[2], actual_hours=float(hours) if hours else None)
    elif sys.argv[1] == "--milestone":
        if len(sys.argv) < 4:
            print(json.dumps({"status": "error", "message": "Missing task id or milestone index"}))
            sys.exit(1)
        task_id = sys.argv[2]
        milestone_idx = int(sys.argv[3])
        note = parse_optional("--note") or ""
        hours = parse_optional("--hours")
        complete_milestone(task_id, milestone_idx, note, actual_hours=float(hours) if hours else None)
    else:
        print(json.dumps({"status": "error", "message": f"Unknown option: {sys.argv[1]}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
