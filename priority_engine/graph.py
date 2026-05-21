"""Dependency graph and topological ordering for tasks."""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Iterator
from .models import Task


class DependencyGraph:
    """
    Directed acyclic graph where edge A→B means A must finish before B.
    Supports:
      - cycle detection (raises on add)
      - topological ordering
      - blocked-set queries (tasks whose deps are not yet complete)
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._adj: dict[str, set[str]] = defaultdict(set)   # id -> dependents
        self._in_degree: dict[str, int] = defaultdict(int)

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task
        if task.id not in self._adj:
            self._adj[task.id] = set()
        for dep in task.dependencies:
            self._adj[dep].add(task.id)
            self._in_degree[task.id] += 1

        if self._has_cycle():
            # Roll back
            for dep in task.dependencies:
                self._adj[dep].discard(task.id)
                self._in_degree[task.id] -= 1
            del self._tasks[task.id]
            raise ValueError(f"Adding task '{task.id}' would create a cycle")

    def _has_cycle(self) -> bool:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self._adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        return any(dfs(n) for n in self._tasks if n not in visited)

    def mark_complete(self, task_id: str) -> list[str]:
        """Mark task done; return IDs that just became unblocked."""
        task = self._tasks.get(task_id)
        if not task:
            return []
        unblocked = []
        for dependent_id in self._adj.get(task_id, []):
            self._in_degree[dependent_id] -= 1
            if self._in_degree[dependent_id] == 0:
                unblocked.append(dependent_id)
        return unblocked

    def is_ready(self, task_id: str) -> bool:
        """True if all dependencies are complete."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        from .models import TaskStatus
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if dep is None or dep.status != TaskStatus.COMPLETED:
                return False
        return True

    def topological_order(self) -> list[Task]:
        """Kahn's algorithm — returns tasks in a valid execution order."""
        in_deg = dict(self._in_degree)
        queue: deque[str] = deque(
            tid for tid in self._tasks if in_deg.get(tid, 0) == 0
        )
        order: list[Task] = []
        while queue:
            tid = queue.popleft()
            order.append(self._tasks[tid])
            for dep in self._adj.get(tid, []):
                in_deg[dep] -= 1
                if in_deg[dep] == 0:
                    queue.append(dep)
        return order

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> Iterator[Task]:
        return iter(self._tasks.values())

    def dependency_edges(self) -> list[tuple[str, str]]:
        """Return (dependency_id, dependent_id) pairs."""
        edges = []
        for src, dests in self._adj.items():
            for dst in dests:
                edges.append((src, dst))
        return edges
