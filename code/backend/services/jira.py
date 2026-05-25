"""Mock Jira integration for engineering task creation.

Production: Replace with real Jira REST API calls.
"""

import time

_task_counter = 5000


def create_engineering_task(summary: str, priority: str = "Medium", assignee: str = "engineering@nvidia.com") -> dict:
    """Mock Jira engineering task creation.

    Production: Replace with real Jira REST API call.

    Args:
        summary: The task summary/description
        priority: Task priority (Low, Medium, High, Critical)
        assignee: The assignee email or username

    Returns:
        Mock Jira task object with ID, key, status, and other details
    """
    global _task_counter
    _task_counter += 1
    
    task = {
        "task_id": _task_counter,
        "key": f"ENG-{_task_counter:04d}",
        "summary": summary,
        "priority": priority,
        "assignee": assignee,
        "status": "To Do",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "issue_type": "Task",
        "labels": ["escalation", "it-support"]
    }
    
    return task