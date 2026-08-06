"""
Email follow-up tool.

Phase 2: Logs email content (doesn't actually send).
Phase 3: Integrate with SendGrid/SES/SMTP.
"""

from freelancer.profile import FreelancerProfile
from typing import Optional
from utils.logging import get_logger

logger = get_logger(__name__)


async def send_followup_email(
    profile: FreelancerProfile,
    email: str,
    name: str,
    summary: Optional[str] = "",
    next_steps: Optional[str] = "",
) -> str:
    """Send a follow-up email after the call."""
    logger.info("send_followup_email", to=email, freelancer=profile.name)

    subject = f"Following up — {profile.name}, {profile.title}"

    body = f"Hi {name},\n\nThanks for chatting!\n\n"

    if summary:
        body += f"What we discussed: {summary}\n\n"
    if next_steps:
        body += f"Next steps: {next_steps}\n\n"

    body += f"About {profile.name}:\n{profile.bio}\n\n"

    if profile.services:
        body += "Services:\n"
        for s in profile.services:
            line = f"  - {s.name}"
            if s.starting_price:
                line += f" (from {s.starting_price})"
            body += line + "\n"
        body += "\n"

    if profile.portfolio_url:
        body += f"Portfolio: {profile.portfolio_url}\n"
    if profile.calendly_url:
        body += f"Book a call: {profile.calendly_url}\n"

    body += f"\nBest,\n{profile.name}\n{profile.email}"

    # Phase 2: Log to console (Phase 3: actually send via email API)
    logger.info("followup_email_content", to=email, subject=subject, body_length=len(body))

    print(f"\n{'='*50}")
    print(f"📧 FOLLOW-UP EMAIL")
    print(f"To: {email}")
    print(f"From: {profile.email}")
    print(f"Subject: {subject}")
    print(f"{'─'*50}")
    print(body)
    print(f"{'='*50}\n")

    return f"I've sent a follow-up email to {email} with {profile.name}'s details."