from __future__ import annotations

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from modules.architecture.generator import ArchitectureResult
from modules.schema.database_generator import DatabaseSchema, TableSpec, FieldSpec
from modules.schema.api_generator import ApiSchema, RouteSpec
from modules.schema.ui_generator import UiSchema, PageSpec, ComponentSpec
from modules.schema.auth_generator import AuthSchema, RoleAuthSpec, RouteGuard
from modules.schema.business_generator import BusinessSchema
from modules.validation.engine import ValidationError, ValidationReport

class RepairStep(BaseModel):
    error_message: str
    classification: str  # missing_table, missing_endpoint, missing_page, missing_permission, etc.
    action_taken: str
    target: str

class RepairReport(BaseModel):
    success: bool
    retry_count: int
    steps: List[RepairStep]

class RepairEngine:
    def repair(
        self,
        errors: List[ValidationError],
        retry_count: int,
        database: DatabaseSchema,
        api: ApiSchema,
        ui: UiSchema,
        auth: AuthSchema,
        business: BusinessSchema
    ) -> RepairReport:
        steps = []
        
        for err in errors:
            classification = "unknown"
            action = "none"

            # 1. Handle missing/invalid login flow tables or endpoints
            if "login" in err.message.lower() or "users" in err.message.lower():
                classification = "missing_login_infrastructure"
                
                # Check if users table missing
                if not any(t.name == "users" for t in database.tables):
                    database.tables.insert(0, TableSpec(
                        name="users",
                        fields=[
                            FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                            FieldSpec(name="email", type="string", unique=True, nullable=False),
                            FieldSpec(name="password_hash", type="string", nullable=False),
                            FieldSpec(name="role", type="string", nullable=False)
                        ]
                    ))
                    action = "Added missing 'users' table to database schema"
                
                # Check if login endpoint missing
                if not any(ep.path == "/api/auth/login" for ep in api.endpoints):
                    api.endpoints.append(RouteSpec(
                        method="POST",
                        path="/api/auth/login",
                        description="Authenticate user and issue session token",
                        request_body={"email": "string", "password": "string"},
                        response_body={"token": "string", "role": "string"}
                    ))
                    action = "Added missing '/api/auth/login' endpoint to API schema"
            
            # 2. Handle missing database fields/columns referred by APIs
            elif "does not correspond to a column in database table" in err.message:
                classification = "missing_column"
                # Extract field name and table name
                # "API request field 'x' does not correspond to a column in database table 'y'"
                parts = err.message.split("'")
                if len(parts) >= 5:
                    field_name = parts[1]
                    table_name = parts[3]
                    
                    # Find table and add field
                    for table in database.tables:
                        if table.name == table_name:
                            # Avoid duplicate field additions
                            if not any(f.name == field_name for f in table.fields):
                                table.fields.append(FieldSpec(
                                    name=field_name,
                                    type="string",  # Default to string type
                                    nullable=True
                                ))
                                action = f"Added missing column '{field_name}' to table '{table_name}'"
                                break

            # 3. Handle auth path route guards mapping to missing API routes
            elif "does not map to any valid API endpoint" in err.message:
                classification = "missing_endpoint"
                parts = err.message.split("'")
                if len(parts) >= 3:
                    guard_path = parts[1]
                    # Create corresponding GET endpoint
                    api.endpoints.append(RouteSpec(
                        method="GET",
                        path=f"/api{guard_path}",
                        description=f"Auto-generated endpoint for route path {guard_path}",
                        response_body={"status": "ok"}
                    ))
                    action = f"Added endpoint GET '/api{guard_path}' to match auth route guard"

            # 4. Handle CRUD flow invalidity
            elif "crud flow invalid" in err.message.lower():
                classification = "missing_crud_endpoints"
                # Extract entity name
                parts = err.message.split("'")
                if len(parts) >= 3:
                    entity = parts[1]
                    ent_lower = entity.lower()
                    
                    # Add missing GET/POST endpoints
                    has_create = any(ep.method == "POST" and ent_lower in ep.path.lower() for ep in api.endpoints)
                    has_read = any(ep.method == "GET" and ent_lower in ep.path.lower() for ep in api.endpoints)
                    
                    if not has_create:
                        api.endpoints.append(RouteSpec(
                            method="POST",
                            path=f"/api/{ent_lower}s",
                            description=f"Create a new {entity}",
                            request_body={"name": "string"},
                            response_body={"id": "int"}
                        ))
                        action = f"Created POST '/api/{ent_lower}s' endpoint to restore CRUD"
                    if not has_read:
                        api.endpoints.append(RouteSpec(
                            method="GET",
                            path=f"/api/{ent_lower}s",
                            description=f"List {entity}s",
                            response_body={"items": "array"}
                        ))
                        action = f"Created GET '/api/{ent_lower}s' endpoint to restore CRUD"
            
            # 5. Handle business premium gate referring to undefined role
            elif "refers to undefined role" in err.message:
                classification = "missing_role"
                parts = err.message.split("'")
                if len(parts) >= 5:
                    undefined_role = parts[3]
                    auth.roles.append(RoleAuthSpec(
                        name=undefined_role,
                        permissions=["read:own", "write:own"]
                    ))
                    action = f"Created missing role '{undefined_role}' in auth spec"

            steps.append(RepairStep(
                error_message=err.message,
                classification=classification,
                action_taken=action,
                target=err.target
            ))

        return RepairReport(
            success=len(steps) > 0,
            retry_count=retry_count + 1,
            steps=steps
        )
