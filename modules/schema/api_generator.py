from __future__ import annotations

import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from modules.architecture.generator import ArchitectureResult

class RouteSpec(BaseModel):
    method: str
    path: str
    description: str
    request_body: Dict[str, str] = Field(default_factory=dict)
    response_body: Dict[str, str] = Field(default_factory=dict)

class ApiSchema(BaseModel):
    endpoints: List[RouteSpec]

def generate_api(architecture: ArchitectureResult) -> ApiSchema:
    """Generate API schema containing routes, methods, and schemas."""
    from modules.utils.llm import call_llm_structured
    res = call_llm_structured(
        messages=[{"role": "user", "content": architecture.model_dump_json()}],
        response_model=ApiSchema,
        system_prompt="You are an API router spec generator. Generate endpoints, methods, and request/response specifications matching the application architecture. Note: all values inside request_body and response_body dictionaries MUST be simple strings describing the type (e.g. 'string', 'int', 'float', 'array'), and MUST NOT be lists, dicts, or nested objects. Crucial: Endpoint paths for entities MUST be formatted exactly as '/api/<plural_lowercase_entity_name>' (e.g., '/api/users', '/api/contacts', '/api/orders', '/api/products'). Do NOT use custom descriptive paths like '/api/contact-management' or '/api/authentication'."
    )
    if res:
        return res

    # Deterministic generation fallback
    endpoints = []

    # Authentication route
    endpoints.append(RouteSpec(
        method="POST",
        path="/api/auth/login",
        description="Authenticate user and issue session token",
        request_body={"email": "string", "password": "string"},
        response_body={"token": "string", "role": "string"}
    ))

    # Standard CRUD endpoints for entities
    for entity in architecture.entities:
        ent_lower = entity.lower()
        if ent_lower == "user":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/users",
                    description="List users (Admin only)",
                    response_body={"users": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/users",
                    description="Register a new user",
                    request_body={"email": "string", "password": "string", "role": "string"},
                    response_body={"id": "int", "email": "string"}
                )
            ])
        elif ent_lower == "contact":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/contacts",
                    description="Retrieve user contacts",
                    response_body={"contacts": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/contacts",
                    description="Create a new contact",
                    request_body={"first_name": "string", "last_name": "string", "email": "string", "phone": "string"},
                    response_body={"id": "int", "first_name": "string"}
                ),
                RouteSpec(
                    method="PUT",
                    path="/api/contacts/{id}",
                    description="Update an existing contact",
                    request_body={"first_name": "string", "last_name": "string", "email": "string", "phone": "string"},
                    response_body={"id": "int", "status": "updated"}
                ),
                RouteSpec(
                    method="DELETE",
                    path="/api/contacts/{id}",
                    description="Delete a contact",
                    response_body={"status": "deleted"}
                )
            ])
        elif ent_lower == "subscription":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/subscriptions",
                    description="Get current subscription details",
                    response_body={"tier": "string", "status": "string"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/subscriptions",
                    description="Subscribe to a subscription tier",
                    request_body={"tier": "string"},
                    response_body={"id": "int", "status": "active"}
                )
            ])
        elif ent_lower == "product":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/products",
                    description="Get catalog products",
                    response_body={"products": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/products",
                    description="Add a new catalog product (Seller/Admin)",
                    request_body={"name": "string", "price": "float", "description": "string"},
                    response_body={"id": "int", "name": "string"}
                )
            ])
        elif ent_lower == "cartitem":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/cart",
                    description="Get items in cart",
                    response_body={"items": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/cart",
                    description="Add item to cart",
                    request_body={"product_id": "int", "quantity": "int"},
                    response_body={"id": "int", "quantity": "int"}
                )
            ])
        elif ent_lower == "order":
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path="/api/orders",
                    description="List orders history",
                    response_body={"orders": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path="/api/orders",
                    description="Checkout and place order",
                    response_body={"id": "int", "total_price": "float", "status": "created"}
                )
            ])
        else:
            # General fallback endpoint
            endpoints.extend([
                RouteSpec(
                    method="GET",
                    path=f"/api/{ent_lower}s",
                    description=f"List {ent_lower} entities",
                    response_body={"items": "array"}
                ),
                RouteSpec(
                    method="POST",
                    path=f"/api/{ent_lower}s",
                    description=f"Create a new {ent_lower} entity",
                    request_body={"name": "string"},
                    response_body={"id": "int"}
                )
            ])

    return ApiSchema(endpoints=endpoints)
