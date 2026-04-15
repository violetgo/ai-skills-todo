# Personal TODO Manager

A Claude Code skill for managing personal tasks with Eisenhower-matrix prioritization, milestone tracking, and dependency resolution.

## Features

- **Priority scoring** — weighted formula combining benefit, urgency, effort, and confidence
- **Eisenhower quadrants** — auto-classifies tasks as Important/Urgent combinations
- **Dynamic urgency** — urgency auto-increases as deadlines approach
- **Start date** — defer tasks to a future date, shown separately until actionable
- **Long-term tasks** — track milestones and progress notes across weeks/months
- **Dependencies** — block tasks until prerequisites complete
- **History review** — query completed tasks by date range with stats

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code (SKILL.md)                │
│              Conversational interface layer              │
│         Routes user intent → script invocation           │
└──────────┬──────┬──────┬──────┬──────┬──────┬───────────┘
           │      │      │      │      │      │
           v      v      v      v      v      v
        init   add   recommend  done  update  review
        .py    .py      .py     .py    .py     .py
           │      │      │      │      │      │
           └──────┴──────┴──┬───┴──────┴──────┘
                            │
                            v
              ┌─────────────────────────────┐
              │    ~/.claude/todo-data/      │
              │                             │
              │  active.json   config.json  │
              │                             │
              │  archive/                   │
              │    2026-04-15.json           │
              │    2026-04-16.json           │
              └─────────────────────────────┘
```

## Task Lifecycle

```
                    ┌─────────┐
         add.py ──> │ pending │
                    └────┬────┘
                         │
            milestone ───┤
            completed    │
                         v
                   ┌────────────┐
                   │ in_progress │  (long_term tasks only)
                   └──────┬─────┘
                          │
             done.py ─────┤
                          v
                    ┌───────────┐     ┌──────────────────┐
                    │ completed │ ──> │ archive/DATE.json │
                    └───────────┘     └──────────────────┘
```

## Recommendation Flow

```
                    active.json
                         │
                         v
              ┌─────────────────────┐
              │  For each task:     │
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────────┐
            v            v                v
    start_date > today?  has unmet deps?  otherwise
            │            │                │
            v            v                v
      ┌───────────┐ ┌─────────┐  ┌──────────────────┐
      │not_started│ │ blocked │  │ Score & rank by   │
      │  group    │ │  group  │  │ quadrant + score  │
      └───────────┘ └─────────┘  └────────┬─────────┘
                                          │
                                          v
                                 ┌─────────────────┐
                                 │  Top N tasks     │
                                 │  + overdue warns │
                                 └─────────────────┘
```

## Priority Scoring

```
score = benefit × 0.35 + urgency × 0.30 + (10 - effort) × 0.15 + confidence × 0.20
                                                                    + momentum_bonus
```

| Factor | Weight | Range | Description |
|--------|--------|-------|-------------|
| Benefit | 0.35 | 1-10 | Impact/value of the task |
| Urgency | 0.30 | 1-10 | Dynamic, increases near deadline |
| Effort | 0.15 | 1-10 | Inverted — low effort scores higher |
| Confidence | 0.20 | 1-10 | How certain this needs doing |
| Momentum | +0-2 | bonus | Long-term tasks with completed milestones |

## Scripts

| Script | Purpose |
|--------|---------|
| `init.py` | Create data directory and default config |
| `add.py '<json>'` | Add a task with auto-scoring |
| `recommend.py [N]` | Get top N priority-ranked tasks |
| `done.py --task <id>` | Complete a task (moves to archive) |
| `done.py --milestone <id> <idx>` | Complete a milestone |
| `update.py --set <id> '<json>'` | Update task fields |
| `review.py <start> [end]` | History report by date range |

## Requirements

Python 3 (stdlib only, no dependencies).
