"""Mock ServiceNow integration for IT Helpdesk Agent demo purposes.

Production: Replace with real ServiceNow REST API calls.
"""

import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TICKETS_FILE = PROJECT_ROOT / "data" / "sn_tickets.json"


def _load_tickets() -> list:
    """Load tickets from JSON file."""
    if not TICKETS_FILE.exists():
        return []
    try:
        with open(TICKETS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_tickets(tickets: list) -> None:
    """Save tickets to JSON file."""
    with open(TICKETS_FILE, 'w') as f:
        json.dump(tickets, f, indent=2)


def _generate_ticket_id() -> str:
    """Generate a new ticket ID based on existing tickets."""
    tickets = _load_tickets()
    if not tickets:
        return "INC-0001"
    
    max_num = 0
    for ticket in tickets:
        ticket_id = ticket.get("ticket_id", "")
        if ticket_id.startswith("INC-"):
            try:
                num = int(ticket_id.split("-")[1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    
    return f"INC-{max_num + 1:04d}"


def create_ticket(issue_type: str, user_email: str, description: str = None) -> dict:
    """Create a new ServiceNow ticket.

    Args:
        issue_type: The type of issue (e.g., "Password Reset", "Hardware Issue")
        user_email: The email address of the user reporting the issue
        description: Optional description of the issue

    Returns:
        Ticket object with ID, status, timestamp, and other details
    """
    tickets = _load_tickets()
    
    ticket = {
        "ticket_id": _generate_ticket_id(),
        "issue_type": issue_type,
        "user_email": user_email,
        "description": description,
        "status": "New",
        "priority": "Medium",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "assigned_to": None,
        "resolution": None
    }
    
    tickets.append(ticket)
    _save_tickets(tickets)
    
    return ticket


def get_ticket(ticket_id: str) -> dict:
    """Get a ticket by ID.

    Args:
        ticket_id: The ID of the ticket to retrieve

    Returns:
        Ticket object if found, None otherwise
    """
    tickets = _load_tickets()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            return ticket
    return None


def list_tickets(status: str = None) -> list:
    """List all tickets, optionally filtered by status.

    Args:
        status: Optional status filter (e.g., "New", "In Progress", "Closed")

    Returns:
        List of ticket objects
    """
    tickets = _load_tickets()
    if status:
        return [t for t in tickets if t["status"].lower() == status.lower()]
    return tickets


def assign_ticket(ticket_id: str, group: str = "China L1 Support") -> str:
    """Assign a ticket to a support group.

    Args:
        ticket_id: The ID of the ticket to assign
        group: The support group to assign the ticket to

    Returns:
        Assignment confirmation message
    """
    tickets = _load_tickets()
    
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            ticket["assigned_to"] = group
            ticket["status"] = "In Progress"
            _save_tickets(tickets)
            return f"Ticket {ticket_id} assigned to {group} successfully"
    
    return f"Ticket {ticket_id} not found"


def close_ticket(ticket_id: str, resolution: str) -> str:
    """Close a ticket with a resolution.

    Args:
        ticket_id: The ID of the ticket to close
        resolution: The resolution description

    Returns:
        Closure confirmation message
    """
    tickets = _load_tickets()
    
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            ticket["status"] = "Closed"
            ticket["resolution"] = resolution
            _save_tickets(tickets)
            return f"Ticket {ticket_id} closed successfully. Resolution: {resolution}"
    
    return f"Ticket {ticket_id} not found"


def update_ticket(ticket_id: str, **kwargs) -> str:
    """Update ticket fields.

    Args:
        ticket_id: The ID of the ticket to update
        kwargs: Fields to update (status, priority, assigned_to, resolution)

    Returns:
        Update confirmation message
    """
    tickets = _load_tickets()
    allowed_fields = {"status", "priority", "assigned_to", "resolution"}
    
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            for key, value in kwargs.items():
                if key in allowed_fields:
                    ticket[key] = value
            _save_tickets(tickets)
            return f"Ticket {ticket_id} updated successfully"
    
    return f"Ticket {ticket_id} not found"