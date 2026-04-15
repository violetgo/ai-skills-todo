---
name: todo
description: >-
  Use when the user wants to manage personal TODO items — add tasks, get priority
  recommendations, mark tasks complete, or review history. Triggers on: /todo,
  todo add, new task, next task, what should I do, mark done, task complete,
  review history, what did I do, 待办, 新任务, 下一步, 完成, 回顾.
---

# Personal TODO Manager

Manage personal TODO items through conversation. Four core functions: add tasks (with priority scoring), recommend next actions, mark complete, review history.

**All data operations are handled by Python scripts** in `~/.claude/skills/todo/scripts/`. Do NOT manually read/write JSON files — always call the scripts via Bash.

## Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| `init.py` | Initialize data directory | `python3 ~/.claude/skills/todo/scripts/init.py` |
| `add.py` | Add a task | `python3 ~/.claude/skills/todo/scripts/add.py '<json>'` |
| `recommend.py` | Get priority-sorted tasks | `python3 ~/.claude/skills/todo/scripts/recommend.py [count]` |
| `done.py` | Mark task/milestone complete | `python3 ~/.claude/skills/todo/scripts/done.py --task <id>` |
| `review.py` | Review history by date range | `python3 ~/.claude/skills/todo/scripts/review.py <start> [end]` |
| `update.py` | Update tasks/milestones/deps | `python3 ~/.claude/skills/todo/scripts/update.py --help` |

## Initialization

On EVERY invocation, first run:
```bash
python3 ~/.claude/skills/todo/scripts/init.py
```
This is idempotent — it creates `~/.claude/todo-data/` and its files only if they don't exist.

## Routing

After initialization, determine which function to invoke based on the user's message:

| User Intent | Function |
|-------------|----------|
| Adding a new task, recording a TODO | Function 1: Add Task |
| Asking what to do next, priorities | Function 2: Recommend Next Actions |
| Reporting something is done/finished | Function 3: Mark Complete |
| Asking about past accomplishments | Function 4: History Review |
| Updating a task, milestone, or dependency | Function 5: Update Task |

If the user's intent is unclear, ask: "What would you like to do? I can: add a task, recommend priorities, mark something done, or review your history."

**Language:** Respond in the same language the user uses. If they write in Chinese, respond in Chinese. If English, respond in English.

## Function 1: Add Task

**Triggers:** `/todo add`, `/todo 录入`, or natural language like "I have a new task", "新任务", "录入待办"

**Flow — ask one question at a time:**

1. Ask: "What's the task? Give me a title and brief description."
2. Ask: "Is this a one-off task or a long-term task (spanning weeks/months with milestones)?"
3. For one_off tasks: Ask "How many hours do you estimate this will take?" For long_term tasks: skip this — hours are tracked per milestone instead.
4. Ask: "What's the deadline?" (Accept flexible formats: "next Friday", "2026-05-01", "end of month". Convert to YYYY-MM-DD.)
5. Ask: "When does this task start? (optional — leave blank if it can start immediately)" (Accept flexible formats, convert to YYYY-MM-DD. If blank, omit the field.)
6. Ask: "On a scale of 1-10, how impactful/beneficial is this task? (1=low impact, 10=critical)"
7. Ask: "On a scale of 1-10, how confident are you that this needs to be done? (1=maybe, 10=definitely)"
8. If long-term task: Ask "What are the milestones? For each, give a title and deadline."
9. Ask: "Does this task depend on any existing tasks? (i.e., must another task finish first)" If yes, run `python3 ~/.claude/skills/todo/scripts/done.py --list` to show active tasks, and let user pick which ones. Pass their IDs as `"depends_on": ["id1", "id2"]`.
10. Ask: "Any tags for this task? (optional, comma-separated)"

**After collecting all answers, summarize the conversation context:**

Before calling the script, review the full conversation that led to this task. Write a `context` field that captures:
- **Why** this task was created (the motivation, trigger, or problem)
- **Key discussion points** — any important decisions, constraints, or trade-offs discussed
- **Related context** — references to other tasks, projects, people, or systems mentioned

This is NOT the task description. It's the background story. Keep it concise (2-5 sentences) but rich enough that the user can recall the full context months later when reviewing history.

**Build JSON and call add.py:**

```bash
python3 ~/.claude/skills/todo/scripts/add.py '{
  "title": "Task title",
  "description": "Brief description",
  "type": "one_off",
  "deadline": "2026-05-01",
  "start_date": "2026-04-20",
  "estimated_hours": 4,
  "scores": {"benefit": 8, "effort": 3, "confidence": 7},
  "tags": ["tag1", "tag2"],
  "context": "Conversation summary: why this task exists, key decisions made, related context..."
}'
```

For long-term tasks, include milestones:
```bash
python3 ~/.claude/skills/todo/scripts/add.py '{
  "title": "Task title",
  "type": "long_term",
  "deadline": "2026-06-30",
  "start_date": null,
  "estimated_hours": 8,
  "scores": {"benefit": 9, "effort": 4, "confidence": 8},
  "milestones": [
    {"title": "Phase 1", "deadline": "2026-05-15", "completed_at": null, "note": ""},
    {"title": "Phase 2", "deadline": "2026-06-30", "completed_at": null, "note": ""}
  ],
  "tags": ["project"]
}'
```

The script auto-calculates: ID, urgency, quadrant, priority_score. It returns the complete task as JSON.

**After the script returns:**
1. Present the created task to the user in a readable format, showing quadrant and priority score.
2. Ask: "Does this look right? You can also override the quadrant if you disagree."
3. If user wants to override quadrant: re-run add.py with `"quadrant": "new_value"` included in the JSON.
4. Confirm: "Task added! You now have N active tasks." (N is in the script output as `active_count`)

## Function 2: Recommend Next Actions

**Triggers:** `/todo next`, `/todo 推荐`, or natural language like "what should I do next", "我接下来该做什么", "下一步"

**Run the script:**
```bash
python3 ~/.claude/skills/todo/scripts/recommend.py
```

Or with a custom count:
```bash
python3 ~/.claude/skills/todo/scripts/recommend.py 3
```

**The script returns JSON with:**
- `tasks`: array of top-priority tasks (sorted by quadrant then score), each with `quadrant_label`, `priority_score`, `deadline`, `days_remaining`, `current_milestone`, `momentum_bonus`
- `overdue`: array of overdue tasks with `days_overdue`
- `total_active`: total number of active tasks

**Format the output for the user:**

1. If `overdue` is non-empty, show warnings first:
   ```
   OVERDUE: "Task title" was due YYYY-MM-DD (N days overdue)
   ```

2. Show the priority table:

| # | Task | Quadrant | Score | Deadline | Remaining |
|---|------|----------|-------|----------|-----------|
| 1 | Task title | Important & Urgent | 9.2 | 2026-04-18 | 3 days |

3. For long-term tasks (where `current_milestone` is not null), add below the row:
   ```
   Milestone: "milestone title" (deadline: YYYY-MM-DD, N/M done)
   ```

4. If `blocked` is non-empty, show after the main table:
   ```
   BLOCKED (waiting on dependencies):
   - "Task B" blocked by: "Task A"
   ```

5. If `not_started` is non-empty, show after blocked:
   ```
   NOT YET STARTED:
   - "Task title" starts YYYY-MM-DD (in N days)
   ```

6. End with: "You have N active tasks total."

## Function 3: Mark Complete

**Triggers:** `/todo done`, `/todo 完成`, or natural language like "finished X", "X is done", "X 做完了", "完成了 X"

**Step 1: Get the task list for matching.**
```bash
python3 ~/.claude/skills/todo/scripts/done.py --list
```

This returns all active tasks with their IDs, titles, types, and milestones.

**Step 2: Match the user's description** against the returned task list using semantic understanding. The user may use abbreviated or paraphrased descriptions — match by meaning, not exact string.

If multiple tasks could match, list them and ask user to pick.

**Step 2.5: Ask for actual hours spent.**
Before calling the script, ask: "How many hours did this actually take?"
- For one_off tasks: ask for total hours
- For milestones: ask for hours spent on this milestone

**Step 3: Complete the task or milestone.**

For a one_off task or completing an entire long_term task:
```bash
python3 ~/.claude/skills/todo/scripts/done.py --task <task_id> --hours <actual_hours>
```

For completing a milestone on a long_term task:
```bash
python3 ~/.claude/skills/todo/scripts/done.py --milestone <task_id> <milestone_index> --note "optional note" --hours <actual_hours>
```

The `milestone_index` is 0-based, from the `--list` output.

**Step 4: Report result.**
The script returns `remaining_active` count. Confirm:
```
"Task title" marked as complete! You have N remaining active tasks.
```

For milestones, confirm:
```
Milestone "milestone title" completed for "task title" (N/M milestones done).
```

## Function 4: History Review

**Triggers:** `/todo review`, `/todo 回顾`, or natural language like "what did I do this week", "我这周做了什么", "past month review", "这个月完成了什么", "季度回顾"

**Time range parsing:**
- "this week" / "这周" / "过去一周" → last 7 days
- "this month" / "这个月" / "过去一个月" → last 30 days
- "this quarter" / "这个季度" / "过去一个季度" → last 90 days
- Specific dates: "from April 1 to April 15" → exact range
- If ambiguous, ask the user to clarify.

**Run the script** (convert time range to YYYY-MM-DD dates):
```bash
python3 ~/.claude/skills/todo/scripts/review.py 2026-04-08 2026-04-15
```

If only start_date given, end_date defaults to today.

**The script returns JSON with:**
- `completed_tasks`: array with date, title, type, quadrant_label, estimated_hours, context
- `long_term_activity`: array of long-term tasks with milestone/progress events in range
- `summary`: total_completed, total_estimated_hours, by_quadrant counts, milestones_completed

**Format the output:**

### Completed Tasks

| Date | Task | Type | Quadrant |
|------|------|------|----------|
| 04-15 | Task A | one_off | Important & Urgent |

For each task that has a non-empty `context`, show it below:
```
   Background: "why this task was created, key discussion points..."
```

### Long-Term Task Progress

(For each entry in long_term_activity)

**"Task title"**
- [MM-DD] Milestone "M1" completed
- [MM-DD] Note: "progress update"

### Summary

- Total completed: N tasks (estimated M hours)
- By quadrant: Important & Urgent: X, Important & Not Urgent: Y, ...
- Long-term tasks: N milestones completed across M tasks

If summary shows 0 completed and 0 milestones:
```
No tasks were completed between YYYY-MM-DD and YYYY-MM-DD.
```

## Function 5: Update Task

**Triggers:** `/todo update`, `/todo 更新`, or natural language like "change the deadline", "add a milestone", "update milestone", "add dependency", "修改里程碑", "调整截止日期"

**Understand what the user wants to change, then call the appropriate update.py command:**

**Milestone operations:**

Add a new milestone:
```bash
python3 ~/.claude/skills/todo/scripts/update.py --add-milestone <task_id> '{"title": "New milestone", "deadline": "2026-06-01"}'
```

Edit an existing milestone (title, deadline, or both):
```bash
python3 ~/.claude/skills/todo/scripts/update.py --edit-milestone <task_id> <milestone_index> '{"title": "Updated title", "deadline": "2026-07-01"}'
```

Remove a milestone:
```bash
python3 ~/.claude/skills/todo/scripts/update.py --remove-milestone <task_id> <milestone_index>
```

**Dependency operations:**

Add a dependency (task B depends on task A):
```bash
python3 ~/.claude/skills/todo/scripts/update.py --add-dep <task_B_id> <task_A_id>
```

Remove a dependency:
```bash
python3 ~/.claude/skills/todo/scripts/update.py --remove-dep <task_B_id> <task_A_id>
```

**General task field updates** (deadline, tags, scores, description, etc.):
```bash
python3 ~/.claude/skills/todo/scripts/update.py --set <task_id> '{"deadline": "2026-08-01", "tags": ["updated"]}'
```

Note: `id`, `created_at`, and `type` are protected and cannot be changed.

**Flow:**
1. First run `python3 ~/.claude/skills/todo/scripts/done.py --list` to show active tasks for the user to identify which task to update.
2. Understand what the user wants to change through conversation.
3. Call the appropriate update.py command.
4. Confirm the change to the user, showing before/after where applicable.
