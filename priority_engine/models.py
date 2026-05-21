"""Core data models for PriorityOS."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    PREEMPTED = "preempted"


@dataclass
class Task:
    id: str
    name: str
    description: str
    urgency: float          # 0-10: time sensitivity
    impact: float           # 0-10: business/user value
    effort_hours: float     # estimated effort
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    preempted_at: Optional[float] = None
    is_injected: bool = False   # flagged True when added mid-execution

    def compute_priority(self) -> float:
        """
        Score = (urgency * 0.45) + (impact * 0.40) + (1/effort * 0.15) * 10
        Injected tasks get a +2 urgency bonus to simulate real interrupt.
        """
        u = min(self.urgency + (2.0 if self.is_injected else 0.0), 10.0)
        effort_factor = (1.0 / max(self.effort_hours, 0.5)) * 10.0
        self.priority_score = round(
            u * 0.45 + self.impact * 0.40 + effort_factor * 0.15, 3
        )
        return self.priority_score

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "urgency": self.urgency,
            "impact": self.impact,
            "effort_hours": self.effort_hours,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "priority_score": self.priority_score,
            "is_injected": self.is_injected,
        }
