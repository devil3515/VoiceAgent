"""
Tool definitions and executor for the voice agent.

Defines all available tools in OpenAI function calling format
and provides an executor that routes tool calls to implementations.
"""

import json
from typing import Any, Callable, Optional

from tools.pricing import lookup_pricing
from tools.appointments import book_appointment, check_availability
from tools.knowledge import search_knowledge
from tools.transfer import transfer_call

from utils.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# TOOL DEFINITIONS (OpenAI function calling format)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_pricing",
            "description": "Look up pricing information for a product plan. Use this when the caller asks about prices, costs, or plan details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_name": {
                        "type": "string",
                        "enum": ["basic", "premium", "enterprise"],
                        "description": "The plan name to look up pricing for",
                    }
                },
                "required": ["plan_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a time slot is available for an appointment. Use this before booking an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (24-hour)",
                    },
                },
                "required": ["date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for the caller. Always check availability first before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Caller's full name",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (24-hour)",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Topic or reason for the appointment",
                    },
                },
                "required": ["name", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the company knowledge base for product information, FAQs, policies, or technical details. Use this when the caller asks a question you're not sure about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or question to look up",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer the call to a human agent. Use this when you cannot help the caller, when they explicitly ask for a human, or when the situation requires human judgment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for transferring the call",
                    },
                    "department": {
                        "type": "string",
                        "enum": ["sales", "support", "billing", "manager"],
                        "description": "Department to transfer to",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


# ─────────────────────────────────────────────
# TOOL EXECUTOR
# ─────────────────────────────────────────────

# Map tool names to their implementations
TOOL_MAP: dict[str, Callable] = {
    "lookup_pricing": lookup_pricing,
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "search_knowledge": search_knowledge,
    "transfer_call": transfer_call,
}


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    call_sid: Optional[str] = None,
) -> str:
    """
    Execute a tool call and return the result as a string.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments (parsed from LLM)
        call_sid: Twilio call SID (for transfer_call)
    
    Returns:
        Tool result as a string
    """
    import time
    start = time.time()

    logger.info(
        "tool_execute_start",
        tool_name=tool_name,
        arguments=arguments,
    )

    # Find the tool implementation
    tool_func = TOOL_MAP.get(tool_name)

    if not tool_func:
        error_msg = f"Unknown tool: {tool_name}"
        logger.error("tool_unknown", tool_name=tool_name)
        return error_msg

    try:
        # Execute the tool
        # Pass call_sid for transfer_call
        if tool_name == "transfer_call" and call_sid:
            result = await tool_func(**arguments, call_sid=call_sid)
        else:
            result = await tool_func(**arguments)

        latency_ms = (time.time() - start) * 1000

        logger.info(
            "tool_execute_complete",
            tool_name=tool_name,
            latency_ms=round(latency_ms, 1),
            result_length=len(str(result)),
        )

        return str(result)

    except TypeError as e:
        logger.error(
            "tool_argument_error",
            tool_name=tool_name,
            error=str(e),
            arguments=arguments,
        )
        return f"Error: Invalid arguments for {tool_name}. {str(e)}"

    except Exception as e:
        logger.error(
            "tool_execute_error",
            tool_name=tool_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return f"Error executing {tool_name}: {str(e)}"


def get_tool_definitions() -> list[dict]:
    """Get all tool definitions in OpenAI format."""
    return TOOL_DEFINITIONS


def get_tool_names() -> list[str]:
    """Get names of all available tools."""
    return list(TOOL_MAP.keys())