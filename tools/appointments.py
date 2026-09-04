"""
Appointment booking tools.

- check_availability: Check if a time slot is free
- book_appointment: Book an appointment

In production, this would connect to Google Calendar, Calendly, etc.
"""


import uuid
from datetime import datetime, timedelta
from typing import Optional

from utils.logging import get_logger

logger=get_logger(__name__)



# ─── Mock booked slots (in production, use a real calendar) ───
_booked_slots: dict[str, list[str]] = {}

def _get_date_key(date: str) -> str:
    """Normalize date to a consistent format."""
    return date.strip()

async def check_availability(date: str, time: str,) -> str:
    """
    Check if a time slot is available for an appointment.

    Args:
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format

    Returns:
        Availability status as a string
    """
    logger.info("availability_check", date=date, time=time)

    try:
        parsed_date=datetime.strptime(date, "%Y-%m-%d")
        if parsed_date.date() < datetime.now().date():
            return "That date has already passed. Could you provide a future date?"

    except ValueError:
        return "I couldn't understand that date. Could you say it in a format like January 15th, 2025?"

    # Check of slot is already booked
    date_key=_get_date_key(date)
    booked=_booked_slots.get(date_key,[])

    if time in booked:
        # Suggest nearby slots
        hour, minuet = time.split(":")
        suggestions=[]
        for offset in [-1, 1, -2, 2]:
            try:
                new_time = datetime.strptime(time, "%H:%M") + timedelta(hours=offset)
                new_time_str = new_time.strftime("%H:%M")
                if new_time_str not in booked:
                    suggestions.append(new_time_str)
            except ValueError:
                continue

        if suggestions:
            suggestion_str= ", ".join(suggestions[:3])
            return f"That time slot is already booked. Available times nearby include {suggestion_str}."
        else:
            return f"That time slot is already booked. Let me check other times for you."

    return f"The time slot on {date} at {time} is available. Would you like me to book it?"



async def book_appointment(
    name: str,
    date: str,
    time: str,
    topic: Optional[str] = "",
)->str:
    """
    Book an appointment.

    Args:
        name: Caller's name
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format
        topic: Optional topic/reason

    Returns:
        Booking confirmation as a string
    """
    logger.info("appointment_book", name=name, date=date, time=time, topic=topic)
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        if parsed_date.date() < datetime.now().date():
            return "I can't book an appointment in the past. Could you provide a future date?"
    except ValueError:
        return "I couldn't understand that date format. Could you try again?"

    # Check if slot is already booked
    date_key = _get_date_key(date)
    booked = _booked_slots.get(date_key, [])

    if time in booked:
        return "That slot just got booked. Would you like me to check other available times?"

    # Book the slot
    if date_key not in _booked_slots:
        _booked_slots[date_key] = []
    _booked_slots[date_key].append(time)

     # Generate booking ID
    booking_id = f"APT-{uuid.uuid4().hex[:5].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Format the date nicely
    formatted_date = parsed_date.strftime("%A, %B %d, %Y")
    result = (
        f"Your appointment is booked! "
        f"Confirmation number: {booking_id}. "
        f"{name}, you're all set for {formatted_date} at {time}."
    )
    if topic:
        result += f" Topic: {topic}."

    return result


