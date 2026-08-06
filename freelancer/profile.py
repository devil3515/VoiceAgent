"""
Freelancer profile model.

Stores everything the agent needs to represent you on calls.
The agent NEVER makes up info — it only uses what's here.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Service(BaseModel):
    """A single service offered by the freelancer."""
    name: str
    description: str
    starting_price: Optional[str] = None
    delivery_time: Optional[str] = None


class FreelancerProfile(BaseModel):
    """Complete freelancer profile."""
    # Identity
    name: str = Field(..., description="Your full name")
    email: str = Field(..., description="Your email address")
    phone: str = Field(..., description="Your phone number")
    title: str = Field(..., description="Your professional title")
    company: Optional[str] = Field(None, description="Company name if applicable")
    bio: str = Field("", description="Short professional bio")

    # Services
    services: list[Service] = Field(default_factory=list)
    hourly_rate: Optional[str] = None
    project_rate: Optional[str] = None

    # Links
    portfolio_url: Optional[str] = None
    calendly_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

    # Availability
    available_from: Optional[str] = None
    working_hours: str = "9am-6pm EST"
    timezone: str = "EST"

    # Preferences
    free_consultation: bool = True
    consultation_duration: str = "30 minutes"
    follow_up_email: bool = True

    # Metadata
    profile_id: Optional[str] = None
    created_at: Optional[datetime] = None

    def get_service_names(self) -> list[str]:
        return [s.name for s in self.services]

    def get_service_by_name(self, name: str) -> Optional[Service]:
        name_lower = name.lower()
        for service in self.services:
            if name_lower in service.name.lower() or service.name.lower() in name_lower:
                return service
        return None

    def to_prompt_context(self) -> str:
        """Convert profile to text injected into the system prompt."""
        lines = [
            f"Name: {self.name}",
            f"Title: {self.title}",
        ]
        if self.company:
            lines.append(f"Company: {self.company}")
        if self.bio:
            lines.append(f"Bio: {self.bio}")

        if self.services:
            lines.append("\nServices Offered:")
            for s in self.services:
                line = f"  - {s.name}: {s.description}"
                if s.starting_price:
                    line += f" (Starting at {s.starting_price})"
                if s.delivery_time:
                    line += f" (Delivery: {s.delivery_time})"
                lines.append(line)

        if self.hourly_rate:
            lines.append(f"Hourly Rate: {self.hourly_rate}")
        if self.project_rate:
            lines.append(f"Project Rate: {self.project_rate}")
        if self.portfolio_url:
            lines.append(f"Portfolio: {self.portfolio_url}")
        if self.linkedin_url:
            lines.append(f"LinkedIn: {self.linkedin_url}")
        if self.github_url:
            lines.append(f"GitHub: {self.github_url}")
        if self.available_from:
            lines.append(f"Available From: {self.available_from}")
        lines.append(f"Working Hours: {self.working_hours}")
        lines.append(f"Timezone: {self.timezone}")
        if self.free_consultation:
            lines.append(f"Free Consultation: Yes ({self.consultation_duration})")
        if self.calendly_url:
            lines.append(f"Book Online: {self.calendly_url}")
        lines.append(f"Email: {self.email}")
        lines.append(f"Phone: {self.phone}")

        return "\n".join(lines)


def get_default_profile() -> FreelancerProfile:
    """Default profile for testing."""
    return FreelancerProfile(
        name="John Doe",
        email="john@example.com",
        phone="+1-555-0123",
        title="Full-Stack Developer & UI/UX Designer",
        bio="I build modern web applications and beautiful user interfaces. 8+ years of experience with React, Node.js, and Python.",
        services=[
            Service(name="Web Application Development", description="Full-stack web apps with React, Next.js, Node.js, or Python", starting_price="$3,000", delivery_time="4-8 weeks"),
            Service(name="UI/UX Design", description="User interface design, prototyping, and design systems", starting_price="$1,500", delivery_time="2-4 weeks"),
            Service(name="API Development", description="REST and GraphQL APIs, backend systems, database design", starting_price="$2,000", delivery_time="2-6 weeks"),
            Service(name="Technical Consulting", description="Architecture review, tech stack selection, code audit", starting_price="$150/hour", delivery_time="Flexible"),
        ],
        hourly_rate="$100-150/hour",
        project_rate="Varies by scope (typically $2,000-$10,000)",
        portfolio_url="https://johndoe.dev",
        calendly_url="https://calendly.com/johndoe/consultation",
        linkedin_url="https://linkedin.com/in/johndoe",
        github_url="https://github.com/johndoe",
        available_from="Immediately",
        free_consultation=True,
        consultation_duration="30 minutes",
    )