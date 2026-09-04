"""
Pricing lookup tool.

Returns pricing information for product plans.
In production, this would query a database or API.
"""

from utils.logging import get_logger

logger = get_logger(__name__)

# ─── Pricing Data (replace with DB/API in production) ───

PRICING_DATA = {
    "basic": {
        "price": "$19/month",
        "annual_price": "$190/year (save $38)",
        "features": [
            "5 users",
            "10GB storage",
            "Email support",
            "Basic analytics",
        ],
    },
    "premium": {
        "price": "$49/month",
        "annual_price": "$490/year (save $98)",
        "features": [
            "25 users",
            "100GB storage",
            "Priority support",
            "Advanced analytics",
            "Custom integrations",
            "API access",
        ],
    },
    "enterprise": {
        "price": "Custom pricing",
        "annual_price": "Custom pricing",
        "features": [
            "Unlimited users",
            "Unlimited storage",
            "Dedicated support manager",
            "Custom analytics",
            "Custom integrations",
            "API access",
            "SLA guarantee",
            "On-premise deployment option",
        ],
        "note": "Contact sales for enterprise pricing",
    },
}


async def lookup_pricing(plan_name: str) -> str:
    """
    Look up pricing for a product plan.

    Args:
        plan_name: One of "basic", "premium", or "enterprise"

    Returns:
        Pricing information as a string
    """
    logger.info("pricing_lookup", plan_name=plan_name)

    plan = PRICING_DATA.get(plan_name.lower())
    if not plan:
        available = ", ".join(PRICING_DATA.keys())
        return f"I couldn't find a plan called '{plan_name}'. Our available plans are: {available}."

    # Build a natural-sounding response
    features_list = ", ".join(plan["features"][:-1]) + f", and {plan['features'][-1]}"

    result=f"The {plan_name} plan is {plan['price']}. It includes {features_list}."

    if "annual_price" in plan:
        result += f" Annual billing is {plan['annual_price']}."
    if "note" in plan:
        result +=f"{plan['note']}."

    logger.info("pricing_lookup_success", plan_name=plan_name, result=result)
    return result
