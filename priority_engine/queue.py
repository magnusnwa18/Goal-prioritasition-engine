"""Min-heap priority queue backed by task priority scores."""

from __future__ import annotations
import heapq
from typing import Optional
from .models import Task, TaskStatus


class PriorityQueue:
    """
    A max-priority queue (internally a min-heap on negative scores).
    Supports O(log n) insert and O(log n) pop.
    Stale entries are lazily removed via a version counter.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, str, Task]] = []
        self._counter = 0          # tie-breaker & staleness guard
        self._version: dict[str, int] = {}  # task_id -> current version

    def push(self, task: Task) -> None:
        task.compute_priority()
        self._counter += 1
        ver = self._counter
        self._version[task.id] = ver
        # Negate score so highest priority pops first
        heapq.heappush(self._heap, (-task.priority_score, ver, task.id, task))

    def pop(self) -> Optional[Task]:
        while self._heap:
            neg_score, ver, tid, task = heapq.heappop(self._heap)
            if self._version.get(tid) == ver:
                return task
        return None

    def peek(self) -> Optional[Task]:
        while self._heap:
            neg_score, ver, tid, task = self._heap[0]
            if self._version.get(tid) == ver:
                return task
            heapq.heappop(self._heap)
        return None

    def reprioritize(self, task: Task) -> None:
        """Invalidate old entry and re-insert with fresh score."""
        self.push(task)

    def remove(self, task_id: str) -> None:
        """Lazy delete — invalidate the version so it's skipped on pop."""
        self._version.pop(task_id, None)

    def all_pending(self) -> list[Task]:
        """Return all valid pending tasks sorted by priority (highest first)."""
        seen: set[str] = set()
        result: list[Task] = []
        for neg_score, ver, tid, task in sorted(self._heap):
            if self._version.get(tid) == ver and tid not in seen:
                if task.status == TaskStatus.PENDING:
                    result.append(task)
                    seen.add(tid)
        result.sort(key=lambda t: t.priority_score, reverse=True)
        return result

    def __len__(self) -> int:
        return sum(
            1 for _, ver, tid, _ in self._heap if self._version.get(tid) == ver
        )
