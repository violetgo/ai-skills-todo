#!/usr/bin/env python3
"""Tests for recommend.py start_date support."""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import date, timedelta

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "recommend.py")


def run_recommend(data_dir, count=None):
    env = os.environ.copy()
    env["TODO_DATA_DIR"] = data_dir
    cmd = [sys.executable, SCRIPT]
    if count is not None:
        cmd.append(str(count))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return json.loads(result.stdout)


def setup_data_dir(tasks):
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "active.json"), "w") as f:
        json.dump({"tasks": tasks}, f)
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


def make_task(id, title, deadline, start_date=None):
    return {
        "id": id,
        "title": title,
        "type": "one_off",
        "created_at": "2026-04-15T10:00:00",
        "deadline": deadline,
        "start_date": start_date,
        "quadrant": "important_urgent",
        "scores": {"benefit": 8, "urgency": 5, "effort": 3, "confidence": 7},
        "priority_score": 7.0,
        "status": "pending",
        "completed_at": None,
        "tags": [],
        "context": "",
        "depends_on": [],
        "estimated_hours": 2,
        "actual_hours": None,
    }


def test_future_start_date_goes_to_not_started():
    future = (date.today() + timedelta(days=30)).isoformat()
    deadline = (date.today() + timedelta(days=60)).isoformat()
    tasks = [make_task("20260415-001", "Future task", deadline, start_date=future)]
    tmp = setup_data_dir(tasks)
    try:
        out = run_recommend(tmp)
        assert len(out["tasks"]) == 0, "Future task should not be in main list"
        assert len(out["not_started"]) == 1
        assert out["not_started"][0]["id"] == "20260415-001"
        assert out["not_started"][0]["days_until_start"] > 0
    finally:
        shutil.rmtree(tmp)


def test_past_start_date_in_main_list():
    past = (date.today() - timedelta(days=5)).isoformat()
    deadline = (date.today() + timedelta(days=10)).isoformat()
    tasks = [make_task("20260415-002", "Started task", deadline, start_date=past)]
    tmp = setup_data_dir(tasks)
    try:
        out = run_recommend(tmp)
        assert len(out["tasks"]) == 1, "Past start_date task should be in main list"
        assert len(out["not_started"]) == 0
    finally:
        shutil.rmtree(tmp)


def test_null_start_date_in_main_list():
    deadline = (date.today() + timedelta(days=10)).isoformat()
    tasks = [make_task("20260415-003", "No start date", deadline, start_date=None)]
    tmp = setup_data_dir(tasks)
    try:
        out = run_recommend(tmp)
        assert len(out["tasks"]) == 1, "Null start_date task should be in main list"
        assert len(out["not_started"]) == 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    test_future_start_date_goes_to_not_started()
    test_past_start_date_in_main_list()
    test_null_start_date_in_main_list()
    print("All recommend.py tests passed.")
