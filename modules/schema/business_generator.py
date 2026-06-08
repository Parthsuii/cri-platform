from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field
from modules.architecture.generator import ArchitectureResult

class PremiumGate(BaseModel):
    feature: str
    gated_roles: List[str] = Field(default_factory=list)
    tier_required: str
    message: str

class ValidationConstraint(BaseModel):
    entity: str
    field: str
    constraint_type: str  # min_length, max_val, format, etc.
    value: str
    message: str

class BusinessSchema(BaseModel):
    premium_gates: List[PremiumGate]
    constraints: List[ValidationConstraint]

def generate_business_rules(architecture: ArchitectureResult) -> BusinessSchema:
    """Generate business rules schema including constraints and premium features gating."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a business rule specification generator. Generate premium tier restrictions and entity validation limits matching the application architecture."},
                    {"role": "user", "content": architecture.model_dump_json()}
                ],
                response_format=BusinessSchema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed:
                return parsed
        except Exception:
            pass

    # Deterministic generation fallback
    premium_gates = []
    constraints = []

    # Check for billing / premium
    has_premium = "Subscription" in architecture.entities

    if has_premium:
        premium_gates.append(PremiumGate(
            feature="Admin Analytics Dashboard",
            gated_roles=["User"],
            tier_required="premium",
            message="Please subscribe to our premium tier to access admin analytics."
        ))

    # Add standard entity validation constraints
    for entity in architecture.entities:
        ent_lower = entity.lower()
        if ent_lower == "user":
            constraints.append(ValidationConstraint(
                entity="users",
                field="email",
                constraint_type="regex",
                value=r"^[^@]+@[^@]+\.[^@]+$",
                message="Email must be a valid email address format."
            ))
            constraints.append(ValidationConstraint(
                entity="users",
                field="password_hash",
                constraint_type="min_length",
                value="6",
                message="Password must be at least 6 characters long."
            ))
        elif ent_lower == "contact":
            constraints.append(ValidationConstraint(
                entity="contacts",
                field="first_name",
                constraint_type="min_length",
                value="1",
                message="First name cannot be empty."
            ))
            constraints.append(ValidationConstraint(
                entity="contacts",
                field="last_name",
                constraint_type="min_length",
                value="1",
                message="Last name cannot be empty."
            ))
        elif ent_lower == "product":
            constraints.append(ValidationConstraint(
                entity="products",
                field="price",
                constraint_type="min_value",
                value="0.01",
                message="Price must be greater than zero."
            ))

    return BusinessSchema(premium_gates=premium_gates, constraints=constraints)
