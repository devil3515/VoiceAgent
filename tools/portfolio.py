"""
Portfolio sharing tool.
"""

from freelancer.profile import FreelancerProfile
from typing import Optional
from utils.logging import get_logger

logger = get_logger(__name__)


async def share_portfolio(
    profile: FreelancerProfile,
    email: str,
    services_interested: Optional[str] = "",
) -> str:
    """Share the freelancer's portfolio via email."""
    logger.info("share_portfolio", email=email)

    result = f"I'll send {profile.name}'s portfolio to {email}. "

    if profile.portfolio_url:
        result += f"You can also check it out at {profile.portfolio_url}. "
    if profile.linkedin_url:
        result += f"Their LinkedIn is at {profile.linkedin_url}. "
    if profile.github_url:
        result += f"Code samples on GitHub at {profile.github_url}. "

    return result