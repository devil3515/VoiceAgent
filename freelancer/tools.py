"""
Tool definitions for the freelancer calling agent.
"""

from freelancer.profile import FreelancerProfile
from utils.logging import get_logger

logger = get_logger(__name__)


def get_freelancer_tool_definitions() -> list[dict]:
    """Get all freelancer tool definitions in OpenAI format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_service_info",
                "description": "Get details about a specific service the freelancer offers. Use when the person asks about services or details about a specific service.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Name of the service (e.g., 'web development', 'design')",
                        }
                    },
                    "required": ["service_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_rates",
                "description": "Get the freelancer's pricing. Use when the person asks about costs, rates, or pricing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Optional: specific service to get rates for",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_consultation",
                "description": "Book a free consultation with the freelancer. Use when the person shows interest and wants to discuss their project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Person's name"},
                        "email": {"type": "string", "description": "Person's email"},
                        "preferred_date": {"type": "string", "description": "Preferred date YYYY-MM-DD or 'flexible'"},
                        "preferred_time": {"type": "string", "description": "Preferred time HH:MM or 'flexible'"},
                        "topic": {"type": "string", "description": "What they want to discuss"},
                    },
                    "required": ["name", "email"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "share_portfolio",
                "description": "Share the freelancer's portfolio via email. Use when the person wants to see work examples.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "Email to send portfolio to"},
                        "services_interested": {"type": "string", "description": "Which services they're interested in"},
                    },
                    "required": ["email"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_followup_email",
                "description": "Send a follow-up email after the call. Use before ending the call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "Email to send to"},
                        "name": {"type": "string", "description": "Person's name"},
                        "summary": {"type": "string", "description": "Brief summary of what was discussed"},
                        "next_steps": {"type": "string", "description": "Suggested next steps"},
                    },
                    "required": ["email", "name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "transfer_to_freelancer",
                "description": "Transfer the call directly to the freelancer. Use when the person asks to talk to them or has a complex question.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for transfer"}
                    },
                    "required": ["reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "end_call",
                "description": "Politely end the call. Use when the conversation is wrapping up.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for ending"}
                    },
                },
            },
        },
    ]


def get_freelancer_tool_map(profile: FreelancerProfile) -> dict:
    """
    Get the tool execution map, bound to a specific freelancer profile.
    Each tool closure captures the profile so it has access to real data.
    """
    from tools.freelancer_services import get_service_info, get_rates
    from tools.consultation_booking import book_consultation
    from tools.portfolio import share_portfolio
    from tools.email_followup import send_followup_email
    from tools.transfer import transfer_call

    async def _get_service_info(service_name: str = "") -> str:
        return await get_service_info(profile, service_name)

    async def _get_rates(service_name: str = "") -> str:
        return await get_rates(profile, service_name)

    async def _book_consultation(**kwargs) -> str:
        return await book_consultation(profile, **kwargs)

    async def _share_portfolio(**kwargs) -> str:
        return await share_portfolio(profile, **kwargs)

    async def _send_followup_email(**kwargs) -> str:
        return await send_followup_email(profile, **kwargs)

    async def _transfer_to_freelancer(reason: str = "", **kwargs) -> str:
        return await transfer_call(reason=reason, department=None, call_sid=kwargs.get("call_sid"))

    async def _end_call(reason: str = "conversation complete") -> str:
        logger.info("freelancer_end_call", reason=reason)
        return f"CALL_END: {reason}"

    return {
        "get_service_info": _get_service_info,
        "get_rates": _get_rates,
        "book_consultation": _book_consultation,
        "share_portfolio": _share_portfolio,
        "send_followup_email": _send_followup_email,
        "transfer_to_freelancer": _transfer_to_freelancer,
        "end_call": _end_call,
    }