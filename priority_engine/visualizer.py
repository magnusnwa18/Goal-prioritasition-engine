"""
Terminal visualizer for PriorityOS.
Uses Rich for a live-updating dashboard showing:
  - Current running task
  - Priority queue leaderboard
  - Dependency graph (ASCII art)
  - Execution timeline
"""

from __future__ import annotations
import time
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich import box

from .models import Task, TaskStatus
from .agent import PriorityAgent

console = Console()


STATUS_COLORS = {
    TaskStatus.PENDING: "cyan",
    TaskStatus.RUNNING: "bold green",
    TaskStatus.COMPLETED: "dim green",
    TaskStatus.BLOCKED: "yellow",
    TaskStatus.PREEMPTED: "bold magenta",
}

STATUS_ICONS = {
    TaskStatus.PENDING: "○",
    TaskStatus.RUNNING: "▶",
    TaskStatus.COMPLETED: "✓",
    TaskStatus.BLOCKED: "⊘",
    TaskStatus.PREEMPTED: "⏸",
}


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 10.0) * width)
    return "█" * filled + "░" * (width - filled)


def _build_queue_table(agent: PriorityAgent) -> Table:
    table = Table(
        title="[bold cyan]Priority Queue[/]",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold white",
        expand=True,
    )
    table.add_column("Rank", style="bold", width=5)
    table.add_column("Task", style="white")
    table.add_column("Status", width=12)
    table.add_column("Score", width=8)
    table.add_column("Urgency", width=7)
    table.add_column("Impact", width=7)
    table.add_column("Priority Bar", width=22)

    snap = agent.snapshot()
    current = snap["current_task"]
    rows: list[Task] = []

    if current:
        ct = agent.graph.get_task(current["id"])
        if ct:
            rows.append(ct)

    rows += agent.queue.all_pending()

    for i, task in enumerate(rows):
        status = task.status
        icon = STATUS_ICONS.get(status, "?")
        color = STATUS_COLORS.get(status, "white")
        rank = "▶ NOW" if status == TaskStatus.RUNNING else f"#{i + 1}"
        injected_marker = " [bold magenta]★[/]" if task.is_injected else ""
        table.add_row(
            f"[bold]{rank}[/]",
            f"[{color}]{task.name}{injected_marker}[/]",
            f"[{color}]{icon} {status.value}[/]",
            f"[bold yellow]{task.priority_score:.2f}[/]",
            f"{task.urgency:.1f}",
            f"{task.impact:.1f}",
            f"[green]{_score_bar(task.priority_score)}[/]",
        )

    # Show blocked tasks too
    for task in agent.graph.all_tasks():
        if task.status == TaskStatus.BLOCKED:
            table.add_row(
                "[dim]—[/]",
                f"[yellow]{task.name}[/]",
                f"[yellow]⊘ blocked[/]",
                f"[dim]{task.priority_score:.2f}[/]",
                f"[dim]{task.urgency:.1f}[/]",
                f"[dim]{task.impact:.1f}[/]",
                f"[dim]{_score_bar(task.priority_score)}[/]",
            )

    return table


def _build_graph_panel(agent: PriorityAgent) -> Panel:
    """ASCII dependency graph."""
    edges = agent.graph.dependency_edges()
    all_tasks = {t.id: t for t in agent.graph.all_tasks()}

    if not edges:
        return Panel("[dim]No dependencies[/]", title="[bold cyan]Dependency Graph[/]")

    lines: list[str] = []
    # Group by dependency source
    dep_map: dict[str, list[str]] = {}
    for src, dst in edges:
        dep_map.setdefault(src, []).append(dst)

    for src, dsts in dep_map.items():
        src_task = all_tasks.get(src)
        if not src_task:
            continue
        src_color = STATUS_COLORS.get(src_task.status, "white")
        src_icon = STATUS_ICONS.get(src_task.status, "?")
        lines.append(f"[{src_color}]{src_icon} {src_task.name}[/]")
        for j, dst in enumerate(dsts):
            dst_task = all_tasks.get(dst)
            if not dst_task:
                continue
            dst_color = STATUS_COLORS.get(dst_task.status, "white")
            dst_icon = STATUS_ICONS.get(dst_task.status, "?")
            connector = "└──" if j == len(dsts) - 1 else "├──"
            lines.append(f"  {connector}▶ [{dst_color}]{dst_icon} {dst_task.name}[/]")

    return Panel(
        "\n".join(lines) or "[dim]empty[/]",
        title="[bold cyan]Dependency Graph[/]",
        border_style="blue",
    )


def _build_log_panel(agent: PriorityAgent, max_lines: int = 10) -> Panel:
    log = agent.event_log()[-max_lines:]
    colored = []
    for line in log:
        if "[RUN]" in line:
            colored.append(f"[bold green]{line}[/]")
        elif "[DONE]" in line:
            colored.append(f"[dim green]{line}[/]")
        elif "[INJECT]" in line:
            colored.append(f"[bold magenta]{line}[/]")
        elif "[PREEMPT]" in line:
            colored.append(f"[bold red]{line}[/]")
        elif "[UNLOCK]" in line:
            colored.append(f"[cyan]{line}[/]")
        else:
            colored.append(f"[dim]{line}[/]")
    return Panel(
        "\n".join(colored) or "[dim]No events yet[/]",
        title="[bold cyan]Event Log[/]",
        border_style="dim",
    )


def _build_header(agent: PriorityAgent, elapsed: float) -> Panel:
    snap = agent.snapshot()
    total = len(list(agent.graph.all_tasks()))
    done = len(snap["history"])
    pct = int((done / total) * 100) if total else 0
    bar_filled = int(pct / 5)
    bar = "[green]" + "█" * bar_filled + "[/][dim]" + "░" * (20 - bar_filled) + "[/]"
    current_name = snap["current_task"]["name"] if snap["current_task"] else "—"
    text = (
        f"[bold white]PriorityOS[/]  •  "
        f"Tasks: [yellow]{done}/{total}[/]  {bar}  [yellow]{pct}%[/]  "
        f"•  Running: [bold green]{current_name}[/]  "
        f"•  Elapsed: [dim]{elapsed:.1f}s[/]"
    )
    return Panel(text, box=box.HEAVY, border_style="blue")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_live(agent: PriorityAgent, inject_after: int = 5, inject_task: Optional[Task] = None) -> None:
    """
    Drive the agent step-by-step while rendering a live Rich dashboard.

    inject_after: complete this many tasks, then inject the surprise task.
    inject_task:  the high-priority task to inject.
    """
    start = time.time()
    injected = False
    completed_count = 0

    with Live(console=console, refresh_per_second=10, screen=True) as live:

        def render() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(_build_header(agent, time.time() - start), size=3),
                Layout(name="body"),
                Layout(_build_log_panel(agent), size=14),
            )
            layout["body"].split_row(
                Layout(_build_queue_table(agent), ratio=2),
                Layout(_build_graph_panel(agent), ratio=1),
            )
            return layout

        live.update(render())
        time.sleep(0.5)

        while agent.queue.peek() is not None or agent.current_task is not None:
            # Inject surprise task mid-run
            if not injected and inject_task and completed_count >= inject_after:
                injected = True
                preempted = agent.inject_task(inject_task)
                live.update(render())
                time.sleep(1.0)   # pause so user can see the preemption

            task = agent.step()
            if task:
                completed_count += 1

            live.update(render())
            time.sleep(0.3)

        # Final render
        live.update(render())
        time.sleep(1.0)

    # Print final summary outside Live context
    _print_summary(agent, time.time() - start)


def _print_summary(agent: PriorityAgent, elapsed: float) -> None:
    console.rule("[bold cyan]Execution Complete[/]")
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold white")
    table.add_column("#", width=4)
    table.add_column("Task")
    table.add_column("Score", width=8)
    table.add_column("Urgency", width=8)
    table.add_column("Impact", width=8)
    table.add_column("Injected", width=9)

    for i, entry in enumerate(agent.history, 1):
        injected_str = "[bold magenta]★ yes[/]" if entry["is_injected"] else "[dim]no[/]"
        table.add_row(
            str(i),
            entry["name"],
            f"[yellow]{entry['priority_score']:.2f}[/]",
            str(entry["urgency"]),
            str(entry["impact"]),
            injected_str,
        )

    console.print(table)
    console.print(f"\n[bold]Total time:[/] {elapsed:.1f}s  |  Tasks completed: {len(agent.history)}")
