from __future__ import annotations

import os
import re
from typing import List
from pydantic import BaseModel, Field

class IntentResult(BaseModel):
    app_type: str = Field(description="The category of the application, e.g. crm, ecommerce, etc.")
    features: List[str] = Field(description="List of specific features requested")
    roles: List[str] = Field(description="List of user roles/personas")
    confidence: float = Field(default=1.0, description="Confidence score of extraction")

def extract_intent(prompt: str) -> IntentResult:
    """Extract structured intent from natural language prompt."""
    from modules.utils.llm import call_llm_structured
    res = call_llm_structured(
        messages=[{"role": "user", "content": prompt}],
        response_model=IntentResult,
        system_prompt="You are a software architect requirements extractor. Extract the structured intent from the user's prompt."
    )
    if res:
        return res

    # Rule-based / Deterministic Extraction
    lowered = prompt.lower()
    
    # Infer App Type
    app_type = "generic"
    if "crm" in lowered or "customer relationship" in lowered:
        app_type = "crm"
    elif "ecommerce" in lowered or "e-commerce" in lowered or "shop" in lowered or "store" in lowered:
        app_type = "ecommerce"
    elif "lms" in lowered or "learning" in lowered or "course" in lowered:
        app_type = "lms"
    elif "erp" in lowered or "enterprise resource" in lowered:
        app_type = "erp"
    elif "ats" in lowered or "applicant tracking" in lowered or "hiring" in lowered:
        app_type = "ats"
    elif "pos" in lowered or "point of sale" in lowered:
        app_type = "pos"
    elif "booking" in lowered or "scheduling" in lowered or "appointment" in lowered:
        app_type = "booking"
    elif "helpdesk" in lowered or "support ticket" in lowered:
        app_type = "helpdesk"
    elif "hrms" in lowered or "payroll" in lowered or "employee management" in lowered:
        app_type = "hrms"
    elif "project management" in lowered or "jira" in lowered or "task tracker" in lowered:
        app_type = "project management"

    # Extract features using bullet points, keywords, or lists
    features = []
    
    # Check bullet points or lines
    lines = [line.strip().lstrip("-*• ").strip() for line in prompt.split("\n") if line.strip()]
    for line in lines[1:]: # skip first line if it's the heading
        if len(line) < 50 and any(keyword in line.lower() for keyword in ["login", "contact", "auth", "sub", "premium", "pay", "dashboard", "analytics", "admin", "chat", "ticket", "user", "product", "cart", "checkout"]):
            features.append(line)
            
    # Default feature fallbacks based on app type if none parsed
    if not features:
        if "login" in lowered or "auth" in lowered:
            features.append("login")
        if "contact" in lowered:
            features.append("contacts")
        if "dashboard" in lowered:
            features.append("dashboard")
        if "analytics" in lowered:
            features.append("admin analytics")
        if "subscription" in lowered or "premium" in lowered:
            features.append("premium subscription")
        if "cart" in lowered:
            features.append("cart")
        if "checkout" in lowered:
            features.append("checkout")
            
    # Absolute fallbacks per app type to ensure robustness
    if not features:
        if app_type == "crm":
            features = ["login", "contacts", "dashboard", "admin analytics", "premium subscription"]
        elif app_type == "ecommerce":
            features = ["login", "catalog", "cart", "checkout", "admin analytics"]
        else:
            features = ["login", "dashboard"]

    # Deduplicate features
    seen = set()
    features = [f for f in features if not (f.lower() in seen or seen.add(f.lower()))]

    # Deduce roles
    roles = ["user"]
    if "admin" in lowered or "analytics" in lowered or app_type in ["crm", "erp", "hrms", "ats"]:
        roles.append("admin")
    if "buyer" in lowered or "customer" in lowered or app_type == "ecommerce":
        roles.append("customer")
    if "seller" in lowered or "vendor" in lowered:
        roles.append("seller")
        
    roles = sorted(list(set(roles)))

    # Confidence calculation
    confidence = 0.95 if app_type != "generic" else 0.70

    return IntentResult(
        app_type=app_type,
        features=features,
        roles=roles,
        confidence=confidence
    )
