"""
Lead management — stores people to call.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from utils.logging import get_logger

logger = get_logger(__name__)


class Lead(BaseModel):
    """A person to call on behalf of the freelancer."""
    name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    context: Optional[str] = None
    source: Optional[str] = None

    # Status
    lead_id: Optional[str] = None
    status: str = "pending"  # pending, called, interested, not_interested, consultation_booked
    called_at: Optional[str] = None
    call_duration_seconds: Optional[float] = None
    call_result: Optional[str] = None
    notes: Optional[str] = None


class LeadManager:
    """Manages leads for outbound calls."""

    def __init__(self):
        self._leads: dict[str, Lead] = {}

    def add_lead(self, lead: Lead) -> str:
        lead_id = f"lead_{len(self._leads) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        lead.lead_id = lead_id
        self._leads[lead_id] = lead
        logger.info("lead_added", lead_id=lead_id, name=lead.name)
        return lead_id

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        return self._leads.get(lead_id)

    def get_pending_leads(self) -> list[Lead]:
        return [l for l in self._leads.values() if l.status == "pending"]

    def update_lead_status(self, lead_id: str, status: str, **kwargs):
        lead = self._leads.get(lead_id)
        if lead:
            lead.status = status
            for key, value in kwargs.items():
                if hasattr(lead, key):
                    setattr(lead, key, value)
            logger.info("lead_status_updated", lead_id=lead_id, status=status)

    def get_all_leads(self) -> list[Lead]:
        return list(self._leads.values())


# Singleton
_lead_manager: Optional[LeadManager] = None

def get_lead_manager() -> LeadManager:
    global _lead_manager
    if _lead_manager is None:
        _lead_manager = LeadManager()
    return _lead_manager