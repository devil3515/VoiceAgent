"""
Freelancer service and rate info tools.
"""

from freelancer.profile import FreelancerProfile
from utils.logging import get_logger

logger = get_logger(__name__)


async def get_service_info(profile: FreelancerProfile, service_name: str = "") -> str:
    """Get info about a specific service or all services."""
    logger.info("get_service_info", service_name=service_name)

    if not service_name or service_name.lower() in ["all", "everything", "list"]:
        services = profile.get_service_names()
        if not services:
            return f"{profile.name} is a {profile.title}. They can share more details on a call."
        service_list = ", ".join(services[:-1]) + f", and {services[-1]}"
        return f"{profile.name} offers {service_list}. Would you like details on any specific service?"

    service = profile.get_service_by_name(service_name)
    if service:
        result = f"{profile.name}'s {service.name} service: {service.description}"
        if service.starting_price:
            result += f" Starting at {service.starting_price}."
        if service.delivery_time:
            result += f" Typical delivery: {service.delivery_time}."
        return result

    available = profile.get_service_names()
    return f"I don't have details on that. {profile.name} offers: {', '.join(available)}. Would you like info on any of those?"


async def get_rates(profile: FreelancerProfile, service_name: str = "") -> str:
    """Get pricing info."""
    logger.info("get_rates", service_name=service_name)

    result = ""

    if service_name:
        service = profile.get_service_by_name(service_name)
        if service and service.starting_price:
            result = f"For {service.name}, {profile.name}'s rates start at {service.starting_price}."

    if not result and profile.hourly_rate:
        result = f"{profile.name}'s hourly rate is {profile.hourly_rate}."

    if profile.project_rate:
        result += f" For projects, rates are typically {profile.project_rate}."

    if not result:
        result = f"I'd need to connect you with {profile.name} for specific pricing. Would you like a free consultation?"

    if profile.free_consultation:
        result += f" They offer a free {profile.consultation_duration} consultation to discuss your needs and provide a quote."

    return result