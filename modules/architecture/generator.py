from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field
from modules.intent.extractor import IntentResult

class ArchitectureResult(BaseModel):
    entities: List[str] = Field(description="Capitalized names of database entities/models")
    roles: List[str] = Field(description="Capitalized list of roles")
    flows: List[str] = Field(description="List of key application workflows")

def generate_architecture(intent: IntentResult) -> ArchitectureResult:
    """Generate architecture specification from application intent."""
    from modules.utils.llm import call_llm_structured
    res = call_llm_structured(
        messages=[{"role": "user", "content": intent.model_dump_json()}],
        response_model=ArchitectureResult,
        system_prompt="You are a software architect generator. Convert the requirements intent into a list of database entities, user roles, and high-level flows. Crucial: Entity names MUST be singular, capitalized names (e.g. 'User', 'Contact', 'Order', 'Product'), and MUST NOT be pluralized (e.g., NOT 'Users', NOT 'Contacts')."
    )
    if res:
        return res

    # Rule-based generation fallback
    roles = [role.capitalize() for role in intent.roles]
    entities = ["User"]
    flows = []

    # Map features to entities and flows
    for feature in intent.features:
        feat_lower = feature.lower()
        if "login" in feat_lower or "auth" in feat_lower:
            if "User" not in entities:
                entities.append("User")
            flows.append("Login User")
        if "contact" in feat_lower:
            if "Contact" not in entities:
                entities.append("Contact")
            flows.extend(["Create Contact", "List Contacts", "Delete Contact"])
        if "dashboard" in feat_lower:
            flows.append("View Dashboard")
        if "analytics" in feat_lower:
            flows.append("View Admin Analytics")
        if "subscription" in feat_lower or "premium" in feat_lower:
            if "Subscription" not in entities:
                entities.append("Subscription")
            flows.append("Subscribe Premium")
        if "cart" in feat_lower:
            if "CartItem" not in entities:
                entities.append("CartItem")
            flows.extend(["Add to Cart", "View Cart"])
        if "checkout" in feat_lower:
            if "Order" not in entities:
                entities.append("Order")
            flows.append("Checkout Order")
        if "catalog" in feat_lower or "product" in feat_lower:
            if "Product" not in entities:
                entities.append("Product")
            flows.append("List Products")

    # Add default flows if none generated
    if not flows:
        flows.append("View Homepage")

    # Ensure capitalization and uniqueness
    entities = sorted(list(set(entities)))
    roles = sorted(list(set(roles)))
    flows = sorted(list(set(flows)))

    return ArchitectureResult(
        entities=entities,
        roles=roles,
        flows=flows
    )
