"""
PriorityOS — Resource & Goal Prioritization Engine
Entry point: loads 10 competing tasks, runs the agent with live terminal visualization,
then injects a critical surprise task mid-execution.
"""

from priority_engine.models import Task
from priority_engine.agent import PriorityAgent
from priority_engine.visualizer import run_live, console

# ---------------------------------------------------------------------------
# 10 Competing Tasks (simulate a real product backlog)
# ---------------------------------------------------------------------------

INITIAL_TASKS: list[Task] = [
    Task(
        id="T01",
        name="Fix auth token expiry bug",
        description="Users get logged out randomly — JWT TTL misconfiguration",
        urgency=9.0, impact=9.5, effort_hours=2.0,
        dependencies=[],
    ),
    Task(
        id="T02",
        name="Optimize DB query (N+1)",
        description="Dashboard loads in 8s; query profiling reveals N+1 on user feed",
        urgency=7.0, impact=8.0, effort_hours=3.0,
        dependencies=["T01"],
    ),
    Task(
        id="T03",
        name="Ship onboarding email flow",
        description="Marketing campaign launches Friday — emails must be live",
        urgency=8.5, impact=7.5, effort_hours=4.0,
        dependencies=[],
    ),
    Task(
        id="T04",
        name="Write unit tests for payments",
        description="Coverage is 12%; payment logic is completely untested",
        urgency=5.0, impact=9.0, effort_hours=6.0,
        dependencies=["T01"],
    ),
    Task(
        id="T05",
        name="Refactor config module",
        description="Globals scattered across 40 files; blocked release pipeline",
        urgency=4.0, impact=6.0, effort_hours=5.0,
        dependencies=[],
    ),
    Task(
        id="T06",
        name="Mobile push notification support",
        description="iOS/Android silent pushes for real-time updates",
        urgency=6.0, impact=8.5, effort_hours=8.0,
        dependencies=["T03"],
    ),
    Task(
        id="T07",
        name="Update privacy policy page",
        description="GDPR compliance deadline end of month",
        urgency=7.5, impact=5.0, effort_hours=1.0,
        dependencies=[],
    ),
    Task(
        id="T08",
        name="Implement CSV export",
        description="Top enterprise feature request — blocks 3 sales deals",
        urgency=6.5, impact=9.0, effort_hours=3.5,
        dependencies=["T02"],
    ),
    Task(
        id="T09",
        name="Set up staging environment",
        description="No staging = all tests run in prod. Risk is extreme.",
        urgency=8.0, impact=7.0, effort_hours=4.0,
        dependencies=["T05"],
    ),
    Task(
        id="T10",
        name="Redesign landing page",
        description="A/B test shows 34% bounce rate; new design is ready",
        urgency=3.5, impact=7.0, effort_hours=6.0,
        dependencies=[],
    ),
]

# ---------------------------------------------------------------------------
# Surprise task injected after 5 completions (simulates a real interrupt)
# ---------------------------------------------------------------------------

CRITICAL_INJECTION = Task(
    id="T11",
    name="CRITICAL: Production DB outage",
    description="Primary DB unreachable — all writes failing. All hands on deck.",
    urgency=10.0, impact=10.0, effort_hours=1.5,
    dependencies=[],
)


def main() -> None:
    console.rule("[bold cyan]PriorityOS — Resource & Goal Prioritization Engine[/]")
    console.print(
        "[dim]Loading 10 competing tasks... scoring urgency, impact & effort...[/]\n"
    )

    agent = PriorityAgent(INITIAL_TASKS)

    console.print("[dim]Starting live execution dashboard. Press Ctrl+C to abort.[/]\n")
    import time; time.sleep(1.0)

    run_live(
        agent,
        inject_after=5,
        inject_task=CRITICAL_INJECTION,
    )


if __name__ == "__main__":
    main()
