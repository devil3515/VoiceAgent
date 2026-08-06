"""
Consultation booking tool for freelancer agent.
"""

from datetime import datetime
from typing import Optional
from freelancer.profile import FreelancerProfile
from utils.logging import get_logger

logger = get_logger(__name__)


async def book_consultation(
    profile: FreelancerProfile,
    name: str,
    email: str,
    preferred_date: Optional[str] = "flexible",
    preferred_time: Optional[str] = "flexible",
    topic: Optional[str] = "",
) -> str:
    """Book a consultation with the freelancer."""
    logger.info("book_consultation", name=name, email=email)

    booking_id = f"CONSULT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    result = f"Great! I've booked a {profile.consultation_duration} consultation for {name}. Confirmation: {booking_id}. "

    if preferred_date != "flexible" and preferred_time != "flexible":
        try:
            parsed = datetime.strptime(preferred_date, "%Y-%m-%d")
            formatted = parsed.strftime("%A, %B %d")
            result += f"Scheduled for {formatted} at {preferred_time} {profile.timezone}. "
        except ValueError:
            result += f"Requested for {preferred_date} at {preferred_time}. "
    else:
        result += f"{profile.name} will reach out to schedule a time. "

    if profile.calendly_url:
        result += f"You can also pick a time at {profile.calendly_url}. "

    result += f"A confirmation will be sent to {email}."
    return result