"""
Call transfer tool.

Transfers the call to a human agent.
In production, this would use Twilio's SIP transfer or Dial verb.
"""

from typing import Optional

from utils.logging import get_logger

logger =get_logger(__name__)



# ─── Transfer destinations (in production, use real phone numbers) ───
TRANSFER_NUMBERS = {
    "sales": "+1-800-555-0101",
    "support": "+1-800-555-0102",
    "billing": "+1-800-555-0103",
    "manager": "+1-800-555-0104",
}


async def transfer_call(
    reason: str,
    department: Optional[str] = None,
    call_sid: Optional[str] = None,
) -> str:
    """
    Transfer the call to a human agent.

    Args:
        reason: Reason for transfer
        department: Department to transfer to (sales, support, billing, manager)
        call_sid: Twilio call SID (for actual transfer)

    Returns:
        Transfer status message
    """
    logger.info(
        "call_transfer",
        reason=reason,
        department=department,
        call_sid=call_sid,
    )

    # In Phase 2, we just log and return a message
    # Actual Twilio transfer will be implemented in Phase 3
    if department:
        number = TRANSFER_NUMBERS.get(department, TRANSFER_NUMBERS["support"])
        return f"TRANSFER_REQUESTED: I'm transferring you to our {department} department. Please hold for a moment."
    else:
        return "TRANSFER_REQUESTED: I'm transferring you to a human agent who can help. Please hold."