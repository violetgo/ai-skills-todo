#!/usr/bin/env python3
"""Update an existing task — milestones, dependencies, or task fields.

Usage:
  python3 update.py --add-milestone <task_id> '<milestone_json>'
  python3 update.py --edit-milestone <task_id> <milestone_idx> '<fields_json>'
  python3 update.py --remove-milestone <task_id> <milestone_idx>
  python3 update.py --set <task_id> '<fields_json>'
  python3 update.py --add-dep <task_id> <depends_on_id>
  python3 update.py --remove-dep <task_id> <depends_on_id>
"""

import json
import os
import sys
from datetime import datetime, date

DATA_DIR = os.environ.get("TODO_DATA_DIR", os.path.expanduser("~/.claude/todo-data"))
ACTIVE_FILE = os.path.join(DATA_DIR, "active.json")


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


def error_exit(msg):
    print(json.dumps({"status": "error", "message": msg}))
    sys.exit(1)


def add_milestone(task_id, milestone_json):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")
    if task.get("type") != "long_term":
        error_exit("Task is not long_term")

    milestone = json.loads(milestone_json)
    milestone.setdefault("completed_at", None)
    milestone.setdefault("note", "")

    task["milestones"].append(milestone)
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "milestone_added",
        "task_id": task_id,
        "milestone": milestone,
        "milestones_total": len(task["milestones"]),
    }, ensure_ascii=False, indent=2))


def edit_milestone(task_id, milestone_idx, fields_json):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")
    if task.get("type") != "long_term":
        error_exit("Task is not long_term")

    milestones = task.get("milestones", [])
    if milestone_idx < 0 or milestone_idx >= len(milestones):
        error_exit(f"Milestone index {milestone_idx} out of range (0-{len(milestones)-1})")

    fields = json.loads(fields_json)
    old = dict(milestones[milestone_idx])
    milestones[milestone_idx].update(fields)
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "milestone_updated",
        "task_id": task_id,
        "milestone_index": milestone_idx,
        "before": old,
        "after": milestones[milestone_idx],
    }, ensure_ascii=False, indent=2))


def remove_milestone(task_id, milestone_idx):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")
    if task.get("type") != "long_term":
        error_exit("Task is not long_term")

    milestones = task.get("milestones", [])
    if milestone_idx < 0 or milestone_idx >= len(milestones):
        error_exit(f"Milestone index {milestone_idx} out of range (0-{len(milestones)-1})")

    removed = milestones.pop(milestone_idx)
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "milestone_removed",
        "task_id": task_id,
        "removed": removed,
        "milestones_remaining": len(milestones),
    }, ensure_ascii=False, indent=2))


def set_fields(task_id, fields_json):
    """Update top-level task fields (deadline, tags, scores, etc.)."""
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")

    fields = json.loads(fields_json)
    # Prevent overwriting structural fields
    protected = {"id", "created_at", "type"}
    for key in protected:
        if key in fields:
            error_exit(f"Cannot modify protected field '{key}'")

    old_values = {k: task.get(k) for k in fields}
    task.update(fields)
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "task_updated",
        "task_id": task_id,
        "changed": {k: {"before": old_values[k], "after": fields[k]} for k in fields},
    }, ensure_ascii=False, indent=2))


def add_dependency(task_id, dep_id):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")

    deps = task.get("depends_on", [])
    if dep_id in deps:
        error_exit(f"Dependency '{dep_id}' already exists")

    # Verify dep_id exists
    _, dep_task = find_task(active, dep_id)
    if dep_task is None:
        error_exit(f"Dependency target '{dep_id}' not found in active tasks")

    deps.append(dep_id)
    task["depends_on"] = deps
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "dependency_added",
        "task_id": task_id,
        "depends_on": dep_id,
        "all_dependencies": deps,
    }, ensure_ascii=False, indent=2))


def remove_dependency(task_id, dep_id):
    active = load_json(ACTIVE_FILE)
    idx, task = find_task(active, task_id)
    if idx == -1:
        error_exit(f"Task '{task_id}' not found")

    deps = task.get("depends_on", [])
    if dep_id not in deps:
        error_exit(f"Dependency '{dep_id}' not found")

    deps.remove(dep_id)
    task["depends_on"] = deps
    save_json(ACTIVE_FILE, active)

    print(json.dumps({
        "status": "ok",
        "action": "dependency_removed",
        "task_id": task_id,
        "removed": dep_id,
        "all_dependencies": deps,
    }, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "status": "error",
            "message": "Usage: update.py --add-milestone|--edit-milestone|--remove-milestone|--set|--add-dep|--remove-dep <task_id> ...",
        }))
        sys.exit(1)

    cmd = sys.argv[1]
    task_id = sys.argv[2]

    if cmd == "--add-milestone":
        if len(sys.argv) < 4:
            error_exit("Missing milestone JSON")
        add_milestone(task_id, sys.argv[3])
    elif cmd == "--edit-milestone":
        if len(sys.argv) < 5:
            error_exit("Missing milestone index or fields JSON")
        edit_milestone(task_id, int(sys.argv[3]), sys.argv[4])
    elif cmd == "--remove-milestone":
        if len(sys.argv) < 4:
            error_exit("Missing milestone index")
        remove_milestone(task_id, int(sys.argv[3]))
    elif cmd == "--set":
        if len(sys.argv) < 4:
            error_exit("Missing fields JSON")
        set_fields(task_id, sys.argv[3])
    elif cmd == "--add-dep":
        if len(sys.argv) < 4:
            error_exit("Missing dependency task ID")
        add_dependency(task_id, sys.argv[3])
    elif cmd == "--remove-dep":
        if len(sys.argv) < 4:
            error_exit("Missing dependency task ID")
        remove_dependency(task_id, sys.argv[3])
    else:
        error_exit(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
