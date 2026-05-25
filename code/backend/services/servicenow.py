"""Mock ServiceNow integration for IT Helpdesk Agent demo purposes.

Production: Replace with real ServiceNow REST API calls.
"""

import time

_ticket_counter = 1000


def create_ticket(issue_type: str, user_email: str) -> dict:
    """Mock ServiceNow ticket creation.

    Production: Replace with real ServiceNow REST API call.

    Args:
        issue_type: The type of issue (e.g., "Password Reset", "Hardware Issue")
        user_email: The email address of the user reporting the issue

    Returns:
        Mock ticket object with ID, status, timestamp, and other details
    """
    global _ticket_counter
    _ticket_counter += 1
    
    ticket = {
        "ticket_id": f"INC-{_ticket_counter:04d}",
        "issue_type": issue_type,
        "user_email": user_email,
        "status": "New",
        "priority": "Medium",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "assigned_to": None,
        "resolution": None
    }
    
    return ticket


def assign_ticket(ticket_id: str, group: str = "China L1 Support") -> str:
    """Mock ticket assignment.

    Production: Replace with real ServiceNow API.

    Args:
        ticket_id: The ID of the ticket to assign (e.g., "INC-1001")
        group: The support group to assign the ticket to

    Returns:
        Assignment confirmation message
    """
    return f"Ticket {ticket_id} assigned to {group} successfully"


def close_ticket(ticket_id: str, resolution: str) -> str:
    """Mock ticket closure.

    Production: Replace with real ServiceNow API.

    Args:
        ticket_id: The ID of the ticket to close (e.g., "INC-1001")
        resolution: The resolution description

    Returns:
        Closure confirmation message
    """
    return f"Ticket {ticket_id} closed successfully. Resolution: {resolution}"