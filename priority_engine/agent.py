"""
PriorityOS Agent — orchestrates task scoring, sequencing, and dynamic
re-prioritization when a high-urgency task is injected mid-execution.
"""

from __future__ import annotations
import json
import time
from typing import Optional
from .models import Task, TaskStatus
from .queue import PriorityQueue
from .graph import DependencyGraph


INJECTION_URGENCY_THRESHOLD = 8.5   # tasks above this preempt the current one


class PriorityAgent:
    def __init__(self, tasks: list[Task]) -> None:
        self.graph = DependencyGraph()
        self.queue = PriorityQueue()
        self.history: list[dict] = []        # execution log
        self.current_task: Optional[Task] = None
        self._event_log: list[str] = []

        for task in tasks:
            self.graph.add_task(task)
            if self.graph.is_ready(task.id):
                self.queue.push(task)
            else:
                task.status = TaskStatus.BLOCKED

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def inject_task(self, task: Task) -> bool:
        """
        Insert a new task mid-execution.
        Returns True if it preempts the currently running task.
        """
        task.is_injected = True
        task.compute_priority()
        self.graph.add_task(task)

        preempted = False
        if (
            self.current_task is not None
            and task.urgency >= INJECTION_URGENCY_THRESHOLD
            and task.priority_score > self.current_task.priority_score
        ):
            self._preempt_current(task)
            preempted = True
        elif self.graph.is_ready(task.id):
            self.queue.push(task)

        self._log(f"[INJECT] '{task.name}' (score={task.priority_score:.2f})"
                  + (" → PREEMPTED current task" if preempted else ""))
        return preempted

    def step(self) -> Optional[Task]:
        """
        Execute the next highest-priority ready task.
        Returns the completed task, or None if the queue is empty.
        """
        if self.current_task is None:
            self.current_task = self.queue.pop()

        task = self.current_task
        if task is None:
            return None

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._log(f"[RUN]    '{task.name}' (score={task.priority_score:.2f})")

        # Simulate work
        time.sleep(0.05)

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        self.current_task = None
        self.history.append(task.to_dict())
        self._log(f"[DONE]   '{task.name}'")

        # Unblock dependents
        for unblocked_id in self.graph.mark_complete(task.id):
            dep_task = self.graph.get_task(unblocked_id)
            if dep_task and dep_task.status == TaskStatus.BLOCKED:
                dep_task.status = TaskStatus.PENDING
                self.queue.push(dep_task)
                self._log(f"[UNLOCK] '{dep_task.name}' is now ready")

        return task

    def run_all(self) -> list[Task]:
        """Process every task until the queue is drained."""
        results = []
        while self.queue.peek() is not None or self.current_task is not None:
            t = self.step()
            if t:
                results.append(t)
        return results

    def snapshot(self) -> dict:
        """Current state as a structured JSON-serialisable dict."""
        pending = self.queue.all_pending()
        return {
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "queue": [t.to_dict() for t in pending],
            "history": self.history,
            "edges": self.graph.dependency_edges(),
        }

    def event_log(self) -> list[str]:
        return list(self._event_log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preempt_current(self, incoming: Task) -> None:
        ct = self.current_task
        ct.status = TaskStatus.PREEMPTED
        ct.preempted_at = time.time()
        self._log(f"[PREEMPT] '{ct.name}' suspended")
        # Re-queue the preempted task so it resumes after incoming finishes
        ct.status = TaskStatus.PENDING
        self.queue.push(ct)
        # Promote incoming to front
        incoming.compute_priority()
        self.queue.push(incoming)
        self.current_task = None

    def _log(self, msg: str) -> None:
        self._event_log.append(msg)
