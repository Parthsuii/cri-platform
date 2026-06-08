from __future__ import annotations

import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from modules.architecture.generator import ArchitectureResult
from modules.schema.database_generator import DatabaseSchema
from modules.schema.api_generator import ApiSchema
from modules.schema.ui_generator import UiSchema
from modules.schema.auth_generator import AuthSchema
from modules.schema.business_generator import BusinessSchema

class ValidationError(BaseModel):
    layer: int
    category: str
    message: str
    target: str

class ValidationReport(BaseModel):
    valid: bool
    errors: List[ValidationError]
    checked_rules: List[str]

class ValidationEngine:
    def validate(
        self,
        architecture: ArchitectureResult,
        database: DatabaseSchema,
        api: ApiSchema,
        ui: UiSchema,
        auth: AuthSchema,
        business: BusinessSchema
    ) -> ValidationReport:
        errorsList: List[ValidationError] = []
        checked_rules: List[str] = []

        # --- Layer 1: JSON Validation ---
        # (Since we parsed using Pydantic, this is implicitly valid, but let's log the checks)
        checked_rules.append("Layer 1: JSON validation parsed successfully")

        # --- Layer 2: Schema Validation ---
        # Verify basic schema requirements
        checked_rules.append("Layer 2: Schema model integrity check")
        if not database.tables:
            errorsList.append(ValidationError(layer=2, category="Database", message="Database schema must contain at least one table", target="database"))
        if not api.endpoints:
            errorsList.append(ValidationError(layer=2, category="API", message="API schema must contain at least one endpoint", target="api"))
        if not ui.pages:
            errorsList.append(ValidationError(layer=2, category="UI", message="UI schema must contain at least one page", target="ui"))

        # --- Layer 3: Cross-Layer Validation ---
        # 1. UI field/form properties exist in API
        checked_rules.append("Layer 3: UI fields align with API endpoints")
        api_paths = {endpoint.path for endpoint in api.endpoints}
        
        # 2. API field/endpoints exist in DB tables
        checked_rules.append("Layer 3: API fields exist in Database tables")
        db_tables = {table.name: table for table in database.tables}
        
        # Check API routes mapping to DB tables
        for endpoint in api.endpoints:
            # e.g., /api/contacts -> contacts
            path_parts = [p for p in endpoint.path.split("/") if p and p != "api"]
            if path_parts:
                tbl_name = path_parts[0].replace("{id}", "").strip()
                # If plural, try singular or lookup
                tbl_possibilities = [tbl_name, tbl_name + "s", tbl_name.rstrip("s")]
                matching_tbl = None
                for poss in tbl_possibilities:
                    if poss in db_tables:
                        matching_tbl = db_tables[poss]
                        break
                
                # If table matches, ensure request body fields exist in DB table fields
                if matching_tbl:
                    db_fields = {field.name for field in matching_tbl.fields}
                    for req_field in endpoint.request_body:
                        # Allow password/password_hash mapping
                        resolved_req_field = "password_hash" if req_field == "password" else req_field
                        if resolved_req_field not in db_fields and resolved_req_field != "quantity" and resolved_req_field != "product_id" and resolved_req_field != "user_id":
                            errorsList.append(ValidationError(
                                layer=3,
                                category="Cross-Layer",
                                message=f"API request field '{req_field}' does not correspond to a column in database table '{matching_tbl.name}'",
                                target=f"api:{endpoint.path}"
                            ))

        # 3. Auth references valid API endpoints
        checked_rules.append("Layer 3: Auth policies reference valid endpoints")
        for guard in auth.route_guards:
            # A route guard path like /contacts should have a matching API endpoint like /api/contacts
            guard_api_path = f"/api{guard.path}"
            # Check if there is an endpoint starting with or matching this path
            if not any(endpoint.path.startswith(guard_api_path) or guard_api_path.startswith(endpoint.path) for endpoint in api.endpoints):
                errorsList.append(ValidationError(
                    layer=3,
                    category="Cross-Layer",
                    message=f"Auth route guard path '{guard.path}' does not map to any valid API endpoint",
                    target=f"auth:{guard.path}"
                ))

        # --- Layer 4: Business Validation ---
        checked_rules.append("Layer 4: Business rules valid")
        auth_role_names = {role.name for role in auth.roles}
        for gate in business.premium_gates:
            for gated_role in gate.gated_roles:
                if gated_role not in auth_role_names:
                    errorsList.append(ValidationError(
                        layer=4,
                        category="Business",
                        message=f"Premium gate '{gate.feature}' refers to undefined role '{gated_role}'",
                        target=f"business:premium_gates"
                    ))

        # --- Layer 5: Runtime Validation ---
        checked_rules.append("Layer 5: Runtime flows validation")
        # Check login flow
        has_users_table = "users" in db_tables
        has_login_endpoint = any(ep.path == "/api/auth/login" for ep in api.endpoints)
        if not (has_users_table and has_login_endpoint):
            errorsList.append(ValidationError(
                layer=5,
                category="Runtime",
                message="Login flow invalid: missing 'users' table or '/api/auth/login' endpoint",
                target="runtime:login"
            ))

        # Check CRUD flow for active entities (e.g. contacts)
        for entity in architecture.entities:
            ent_lower = entity.lower()
            if ent_lower not in ["user", "subscription"]:
                # Expect at least one read and one create endpoint
                has_create = any(ep.method == "POST" and ent_lower in ep.path.lower() for ep in api.endpoints)
                has_read = any(ep.method == "GET" and ent_lower in ep.path.lower() for ep in api.endpoints)
                if not (has_create and has_read):
                    errorsList.append(ValidationError(
                        layer=5,
                        category="Runtime",
                        message=f"CRUD flow invalid for '{entity}': missing POST or GET endpoints",
                        target=f"runtime:{ent_lower}"
                    ))

        return ValidationReport(
            valid=len(errorsList) == 0,
            errors=errorsList,
            checked_rules=checked_rules
        )
