"""
Example: build your own task list and run PriorityOS programmatically.
Shows how to use the engine as a library without the live visualizer.
"""

import json
from priority_engine.models import Task
from priority_engine.agent import PriorityAgent

tasks = [
    Task(id="A", name="Write proposal",  description="Draft project proposal",   urgency=7, impact=8,  effort_hours=2),
    Task(id="B", name="Gather data",     description="Collect research data",    urgency=6, impact=7,  effort_hours=3),
    Task(id="C", name="Build prototype", description="Code the MVP",             urgency=5, impact=9,  effort_hours=8, dependencies=["A","B"]),
    Task(id="D", name="Demo to client",  description="Present working prototype",urgency=9, impact=10, effort_hours=1, dependencies=["C"]),
]

agent = PriorityAgent(tasks)

# Mid-way inject an urgent compliance task
completed = 0
results = []
while agent.queue.peek() or agent.current_task:
    if completed == 1:
        agent.inject_task(Task(
            id="X", name="Compliance audit", description="Urgent legal audit",
            urgency=9.5, impact=8, effort_hours=1.5
        ))
    t = agent.step()
    if t:
        completed += 1
        results.append(t)

print(json.dumps(agent.snapshot(), indent=2))
print("\nExecution order:", " → ".join(t.name for t in results))
