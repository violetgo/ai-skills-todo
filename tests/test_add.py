#!/usr/bin/env python3
"""Tests for add.py start_date support."""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import date

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "add.py")


def run_add(task_json, data_dir):
    """Run add.py with a custom DATA_DIR."""
    env = os.environ.copy()
    env["TODO_DATA_DIR"] = data_dir
    result = subprocess.run(
        [sys.executable, SCRIPT, json.dumps(task_json)],
        capture_output=True, text=True, env=env,
    )
    return json.loads(result.stdout)


def setup_data_dir():
    """Create a temp data dir with required files."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "active.json"), "w") as f:
        json.dump({"tasks": []}, f)
    with open(os.path.join(tmp, "config.json"), "w") as f:
        json.dump({
            "weights": {"benefit": 0.35, "urgency": 0.3, "effort": 0.15, "confidence": 0.2},
            "quadrant": {"urgent_days": 14, "important_threshold": 7},
            "dynamic_urgency": {"levels": [
                {"days_lte": 3, "urgency_min": 10},
                {"days_lte": 7, "urgency_min": 8},
            ]},
            "momentum_bonus_max": 2.0,
            "recommend_count": 5,
        }, f)
    os.makedirs(os.path.join(tmp, "archive"))
    return tmp


def test_add_with_start_date():
    tmp = setup_data_dir()
    try:
        task_input = {
            "title": "Future task",
            "description": "Starts later",
            "type": "one_off",
            "deadline": "2026-06-01",
            "estimated_hours": 2,
            "scores": {"benefit": 5, "effort": 3, "confidence": 7},
            "start_date": "2026-05-01",
        }
        out = run_add(task_input, tmp)
        assert out["status"] == "ok"
        assert out["task"]["start_date"] == "2026-05-01"
    finally:
        shutil.rmtree(tmp)


def test_add_without_start_date():
    tmp = setup_data_dir()
    try:
        task_input = {
            "title": "Immediate task",
            "description": "No start date",
            "type": "one_off",
            "deadline": "2026-06-01",
            "estimated_hours": 2,
            "scores": {"benefit": 5, "effort": 3, "confidence": 7},
        }
        out = run_add(task_input, tmp)
        assert out["status"] == "ok"
        assert out["task"]["start_date"] is None
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    test_add_with_start_date()
    test_add_without_start_date()
    print("All add.py tests passed.")
