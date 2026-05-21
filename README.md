# PriorityOS — Resource & Goal Prioritization Engine

> A multi-goal agent that receives 10 competing tasks, assigns urgency/impact scores, sequences them optimally, and **re-prioritizes dynamically** when a critical task arrives mid-execution.

---

## What It Does

Real products never have just one thing to do. They have 10 things that are all "urgent", 3 that are secretly most important, 2 with hard dependencies, and 1 production fire that lands halfway through the sprint.

**PriorityOS** models this reality as a live agent:

1. Loads 10 competing tasks with urgency, impact, and effort dimensions
2. Scores each task using a weighted formula
3. Builds a dependency graph to determine a safe execution order
4. Runs a priority queue that always serves the highest-value ready task
5. Detects a mid-run critical injection (simulating a Slack @ or production alert)
6. **Preempts the current task**, promotes the critical task to the front
7. Re-queues the suspended task and resumes normal prioritization after

All of this is rendered as a **live Rich terminal dashboard** — queue leaderboard, dependency graph, event log, and progress bar updating in real time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          PriorityOS Agent                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Task Loader  │───▶│ Priority Scorer  │───▶│ Priority Queue│  │
│  │  (JSON/code)  │    │  urgency×0.45   │    │  (max-heap)   │  │
│  └──────────────┘    │  impact ×0.40   │    └──────┬────────┘  │
│                       │  effort ×0.15   │           │           │
│                       └──────────────────┘    step()│           │
│                                                      ▼           │
│  ┌──────────────────────┐              ┌─────────────────────┐  │
│  │  Dependency Graph     │◀────────────│    Execution Loop    │  │
│  │  (DAG + Kahn's sort)  │  unblocks   │  mark_complete()     │  │
│  └──────────────────────┘             └──────────┬──────────┘  │
│                                                   │             │
│                                       ┌───────────▼──────────┐  │
│              inject_task() ──────────▶│  Preemption Handler   │  │
│              (mid-execution)          │  urgency ≥ 8.5 →      │  │
│                                       │  suspend + re-queue    │  │
│                                       └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
           ┌─────────────────────────────────────┐
           │       Rich Terminal Visualizer        │
           │  ┌─────────────┐  ┌───────────────┐ │
           │  │ Queue Table  │  │ Dep. Graph    │ │
           │  │ (live ranks) │  │ (ASCII tree)  │ │
           │  └─────────────┘  └───────────────┘ │
           │  ┌────────────────────────────────┐  │
           │  │ Event Log (color-coded stream)  │  │
           │  └────────────────────────────────┘  │
           └─────────────────────────────────────┘
```

---

## Component Breakdown

### `priority_engine/models.py` — Task Data Model

Each task carries:

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier |
| `urgency` | 0–10 | Time sensitivity (deadline pressure) |
| `impact` | 0–10 | Business / user value |
| `effort_hours` | float | Estimated work hours |
| `dependencies` | list[str] | Task IDs that must complete first |
| `priority_score` | float | Computed composite score |
| `is_injected` | bool | True if added mid-execution |

**Priority Formula:**
```
score = (urgency × 0.45) + (impact × 0.40) + ((10 / effort_hours) × 0.15)
```
Injected tasks receive a **+2 urgency bonus** to model real interrupt pressure.

---

### `priority_engine/queue.py` — Max-Priority Queue

- Backed by Python's `heapq` (min-heap on negated scores)
- **O(log n) insert and pop**
- Lazy deletion via version counters — no full re-sort on reprioritization
- `reprioritize(task)` invalidates the old heap entry and re-inserts

---

### `priority_engine/graph.py` — Dependency Graph (DAG)

- Directed Acyclic Graph: edge A → B means "A must finish before B"
- **Cycle detection** on every `add_task()` — raises `ValueError` if violated
- `topological_order()` via Kahn's algorithm
- `mark_complete(id)` returns the list of tasks that just became unblocked
- `is_ready(id)` checks all upstream deps are COMPLETED

---

### `priority_engine/agent.py` — Execution Agent

The heart of PriorityOS:

- Initializes with a list of tasks — blocked ones enter BLOCKED state, ready ones enter the queue
- `step()` pops the top task, runs it, marks complete, unblocks dependents
- `inject_task(task)` triggers preemption logic:
  - If `urgency ≥ 8.5` AND score > current task → current task is **suspended + re-queued**, injected task runs next
  - Otherwise injection joins the queue at its natural priority position
- `run_all()` for headless (no visualization) batch execution
- `snapshot()` returns full structured JSON state at any moment

---

### `priority_engine/visualizer.py` — Live Terminal Dashboard

Built with [Rich](https://github.com/Textualize/rich):

- **Priority Queue Leaderboard** — rank, task name, status icon, score bar
- **Dependency Graph Panel** — ASCII tree showing upstream/downstream relationships and status colors
- **Event Log** — color-coded stream (green=run, magenta=inject, red=preempt, cyan=unblock)
- **Header Bar** — progress bar, current task, elapsed time
- All panels refresh at 10 Hz via `rich.live.Live`

---

## The 10 Competing Tasks

| ID | Task | Urgency | Impact | Effort | Deps |
|----|------|---------|--------|--------|------|
| T01 | Fix auth token expiry bug | 9.0 | 9.5 | 2h | — |
| T02 | Optimize DB query (N+1) | 7.0 | 8.0 | 3h | T01 |
| T03 | Ship onboarding email flow | 8.5 | 7.5 | 4h | — |
| T04 | Write unit tests for payments | 5.0 | 9.0 | 6h | T01 |
| T05 | Refactor config module | 4.0 | 6.0 | 5h | — |
| T06 | Mobile push notification support | 6.0 | 8.5 | 8h | T03 |
| T07 | Update privacy policy page | 7.5 | 5.0 | 1h | — |
| T08 | Implement CSV export | 6.5 | 9.0 | 3.5h | T02 |
| T09 | Set up staging environment | 8.0 | 7.0 | 4h | T05 |
| T10 | Redesign landing page | 3.5 | 7.0 | 6h | — |
| **T11** | **CRITICAL: Production DB outage** | **10.0** | **10.0** | **1.5h** | **injected at task #6** |

---

## Dependency Graph

```
T01 (Fix auth bug)
 ├──▶ T02 (DB query opt.)
 │     └──▶ T08 (CSV export)
 └──▶ T04 (Payment tests)

T03 (Onboarding emails)
 └──▶ T06 (Push notifications)

T05 (Refactor config)
 └──▶ T09 (Staging env)

T07, T10  (no dependencies)
```

---

## Key Results & Observations

### Prioritization is non-obvious

The highest urgency task (T01, u=9.0) runs first — but T07 (Privacy Policy, u=7.5, effort=1h) jumps ahead of T03 (u=8.5, effort=4h) because its low effort multiplies its composite score. **Short high-value tasks are systematically underestimated by raw urgency ranking.**

### Dependency unlocking cascades

Completing T01 immediately unblocks both T02 and T04. Completing T02 unblocks T08. Completing T05 unblocks T09. The queue reorders after each unlock — the agent doesn't plan ahead, it reacts.

### Mid-execution injection

After completing 5 tasks, T11 (Production DB Outage, u=10, i=10) is injected. Because it clears the preemption threshold (`urgency ≥ 8.5`) and its score (9.58) exceeds the current running task, it:
1. Suspends the current task (status → PREEMPTED)
2. Re-queues the suspended task at its original score
3. Runs T11 immediately
4. Resumes the suspended task next

This models real-world interrupt handling: a production fire preempts sprint work, then the team continues where they left off.

### Typical execution order

```
T01 → T07 → T03 → T09* → T02 → [INJECT T11] → T11 → T04 → T06* → T08 → T10
                                                     (* unblocked mid-run)
```

---

## Running It

```bash
# Install dependencies
pip install -r requirements.txt

# Live dashboard (recommended)
python main.py

# Headless batch mode (library usage)
PYTHONPATH=. python examples/custom_tasks.py
```

### Requirements

- Python 3.11+
- `rich >= 13.0` (terminal rendering)
- `anthropic >= 0.20` (optional — for LLM-assisted task scoring extension)

---

## Extending PriorityOS

### LLM-assisted scoring

Replace the static urgency/impact fields with a Claude API call that reads a natural-language task description and returns structured scores:

```python
import anthropic, json

client = anthropic.Anthropic()

def score_task(description: str) -> dict:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                f"Score this engineering task for urgency (0-10) and impact (0-10).\n"
                f"Task: {description}\n"
                f"Return JSON: {{\"urgency\": N, \"impact\": N, \"reasoning\": \"...\"}}"
            )
        }]
    )
    return json.loads(response.content[0].text)
```

### Real-time injection via webhook

Wire `agent.inject_task()` to a webhook endpoint (FastAPI/Flask) to accept Slack slash commands, PagerDuty alerts, or GitHub issue webhooks as real-time task injections.

### Persistent queue (Redis)

Swap `PriorityQueue` backend for Redis sorted sets — `ZADD` for insert, `ZPOPMAX` for pop — to support distributed multi-worker execution.

---

## Project Structure

```
Goal-prioritasition-engine/
├── main.py                          # Entry point — runs live dashboard
├── requirements.txt
├── setup.py
├── priority_engine/
│   ├── __init__.py
│   ├── models.py                    # Task dataclass + priority formula
│   ├── queue.py                     # Max-heap priority queue
│   ├── graph.py                     # DAG + topological sort + cycle detection
│   ├── agent.py                     # Orchestration + preemption logic
│   └── visualizer.py               # Rich live terminal dashboard
└── examples/
    └── custom_tasks.py              # Library usage example
```

---

## Design Decisions

**Why a min-heap with negated scores instead of `sorted()`?**
Insertion and pop are O(log n). Re-sorting the entire list on every task completion or injection is O(n log n) — the heap keeps it fast as the backlog grows.

**Why lazy deletion for reprioritization?**
Heap entries are immutable once inserted. Rather than scanning O(n) to find and remove the old entry, we bump a version counter. The stale entry is silently skipped when it surfaces at pop time. Zero extra allocations.

**Why 8.5 as the preemption threshold?**
Tasks with urgency ≥ 8.5 are genuinely time-critical (production outages, legal deadlines, customer-blocking bugs). Below that, interrupting in-progress work creates context-switch overhead that costs more than it saves. The threshold is configurable via `INJECTION_URGENCY_THRESHOLD` in `agent.py`.

**Why simulate work with `time.sleep(0.05)`?**
The engine is about scheduling logic, not actual execution. The tiny sleep lets the Rich live view animate realistically while keeping the demo fast (full 11-task run completes in ~5 seconds).

---

## License

MIT
