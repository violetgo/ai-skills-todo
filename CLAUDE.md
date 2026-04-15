# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (personal TODO manager) implemented as Python 3 scripts. It manages tasks with Eisenhower-matrix prioritization, milestone tracking, and dependency resolution. Data lives in `~/.claude/todo-data/` (not in this repo). The skill definition is in `SKILL.md`.

## Running Scripts

All scripts use Python 3 stdlib only (no dependencies, no venv needed):

```bash
python3 scripts/init.py                          # Idempotent data dir setup
python3 scripts/add.py '<json>'                   # Create task
python3 scripts/recommend.py [count]              # Priority-ranked task list
python3 scripts/done.py --task <id> [--hours N]   # Complete task (archives it)
python3 scripts/done.py --milestone <id> <idx>    # Complete milestone
python3 scripts/done.py --list                    # List active tasks with IDs
python3 scripts/review.py <start> [end]           # History report (YYYY-MM-DD)
python3 scripts/update.py --set <id> '<json>'     # Update task fields
python3 scripts/update.py --add-milestone <id> '<json>'
python3 scripts/update.py --add-dep <id1> <id2>   # id1 depends on id2
```

All scripts accept JSON via CLI arg and output JSON to stdout. Errors use `{"status": "error", "message": "..."}`.

## Architecture

**Data flow**: Every script reads/writes `~/.claude/todo-data/active.json`. Completed tasks get moved to `~/.claude/todo-data/archive/YYYY-MM-DD.json`. Config (scoring weights, thresholds) is in `~/.claude/todo-data/config.json`.

**Priority scoring** (`add.py`, `recommend.py`): Weighted formula — benefit (0.35) + urgency (0.30) + inverse-effort (0.15) + confidence (0.20). Urgency is dynamic: tasks within 3 days get minimum urgency 10, within 7 days get minimum 8. Long-term tasks with completed milestones get a momentum bonus (up to +2.0).

**Quadrant assignment**: Eisenhower matrix based on `urgent_days=14` and `important_threshold=7` (benefit score). Quadrant is auto-calculated but can be overridden.

**Task types**: `one_off` (hours at task level) vs `long_term` (hours tracked per milestone, has `milestones[]` and `progress_notes[]`).

**Start date**: Optional `start_date` field (YYYY-MM-DD or null). Tasks with a future start_date are excluded from the main recommendation list and shown in a `not_started` group. Their urgency is fixed at 1 until start_date arrives.

**Dependency resolution** (`recommend.py`): Blocked tasks (unmet `depends_on`) are excluded from the main ranking and reported separately. Checks both active and archived task IDs.

**ID format**: `YYYYMMDD-NNN` (date + zero-padded sequence number).

**Protected fields** in `update.py --set`: `id`, `created_at`, `type` cannot be modified.

## Testing

Tests must use an isolated data directory (e.g. a temp dir), never `~/.claude/todo-data/`. Set or patch `DATA_DIR` to point to the test directory to avoid reading or modifying the user's real tasks.

## Key Conventions

- Scripts share `load_json`/`save_json` helpers but each script is self-contained (no shared module).
- `effective_deadline()` in `recommend.py` uses the earlier of task deadline and next incomplete milestone deadline.
- Completing a milestone on a `pending` long-term task auto-transitions status to `in_progress`.
- Archive files are named by completion date, not task creation date.
