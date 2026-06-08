from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field
from modules.architecture.generator import ArchitectureResult

class PermissionSpec(BaseModel):
    action: str
    resource: str
    description: str

class RoleAuthSpec(BaseModel):
    name: str
    permissions: List[str]

class RouteGuard(BaseModel):
    path: str
    allowed_roles: List[str]

class AuthSchema(BaseModel):
    roles: List[RoleAuthSpec]
    route_guards: List[RouteGuard]

def generate_auth(architecture: ArchitectureResult) -> AuthSchema:
    """Generate authentication schema containing roles, permissions, and route guards."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an RBAC policy schema generator. Generate roles, specific resource permission rules, and route guards matching the application architecture."},
                    {"role": "user", "content": architecture.model_dump_json()}
                ],
                response_format=AuthSchema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed:
                return parsed
        except Exception:
            pass

    # Deterministic generation fallback
    roles = []
    route_guards = []

    # Map architecture roles to auth roles
    for role in architecture.roles:
        role_lower = role.lower()
        permissions = []
        if role_lower == "admin":
            permissions = ["read:all", "write:all", "delete:all", "view:admin_dashboard", "manage:users"]
        elif role_lower == "user":
            permissions = ["read:own", "write:own", "create:contacts", "read:contacts", "delete:contacts"]
        elif role_lower == "customer":
            permissions = ["read:catalog", "write:cart", "create:orders", "read:orders"]
        elif role_lower == "seller":
            permissions = ["read:catalog", "create:products", "update:products"]
        else:
            permissions = ["read:own", "write:own"]

        roles.append(RoleAuthSpec(name=role, permissions=permissions))

    # General route protection guards
    route_guards.append(RouteGuard(path="/dashboard", allowed_roles=["Admin", "User", "Customer", "Seller"]))
    route_guards.append(RouteGuard(path="/admin", allowed_roles=["Admin"]))

    for entity in architecture.entities:
        ent_lower = entity.lower()
        if ent_lower == "contact":
            route_guards.append(RouteGuard(path="/contacts", allowed_roles=["Admin", "User"]))
        elif ent_lower == "subscription":
            route_guards.append(RouteGuard(path="/billing", allowed_roles=["Admin", "User"]))
        elif ent_lower == "product":
            route_guards.append(RouteGuard(path="/products", allowed_roles=["Admin", "Customer", "Seller"]))
        elif ent_lower == "cartitem":
            route_guards.append(RouteGuard(path="/cart", allowed_roles=["Customer"]))
        elif ent_lower == "order":
            route_guards.append(RouteGuard(path="/orders", allowed_roles=["Admin", "Customer"]))

    return AuthSchema(roles=roles, route_guards=route_guards)
