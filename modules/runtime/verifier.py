from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

from modules.architecture.generator import ArchitectureResult
from modules.schema.database_generator import DatabaseSchema
from modules.schema.api_generator import ApiSchema
from modules.schema.ui_generator import UiSchema
from modules.schema.auth_generator import AuthSchema
from modules.schema.business_generator import BusinessSchema

class RuntimeCheck(BaseModel):
    flow: str
    component: str
    passed: bool
    details: str

class RuntimeReport(BaseModel):
    passed: bool
    checks: List[RuntimeCheck]

class RuntimeVerifier:
    def verify(
        self,
        architecture: ArchitectureResult,
        database: DatabaseSchema,
        api: ApiSchema,
        ui: UiSchema,
        auth: AuthSchema,
        business: BusinessSchema
    ) -> RuntimeReport:
        checks = []

        db_tables = {table.name for table in database.tables}
        api_paths = {(ep.method, ep.path) for ep in api.endpoints}
        ui_routes = {page.path for page in ui.pages}
        auth_roles = {role.name for role in auth.roles}

        # 1. Login Flow Checks
        has_users_table = "users" in db_tables
        has_login_endpoint = ("POST", "/api/auth/login") in api_paths
        has_login_page = "/login" in ui_routes
        
        checks.append(RuntimeCheck(
            flow="Login Flow",
            component="Database (users table)",
            passed=has_users_table,
            details="Verifies if 'users' table exists for credential validation"
        ))
        checks.append(RuntimeCheck(
            flow="Login Flow",
            component="API (/api/auth/login)",
            passed=has_login_endpoint,
            details="Verifies if login route exists to issue JWT credentials"
        ))
        checks.append(RuntimeCheck(
            flow="Login Flow",
            component="UI (/login page)",
            passed=has_login_page,
            details="Verifies if login form page is designed"
        ))

        # 2. CRUD Flow Checks
        # For contacts or any secondary entities, check CRUD operations
        has_crud_table = "contacts" in db_tables
        has_c = ("POST", "/api/contacts") in api_paths
        has_r = ("GET", "/api/contacts") in api_paths
        has_u = ("PUT", "/api/contacts/{id}") in api_paths or ("PATCH", "/api/contacts/{id}") in api_paths
        has_d = ("DELETE", "/api/contacts/{id}") in api_paths
        
        checks.append(RuntimeCheck(
            flow="CRUD Flow",
            component="Contacts Operations",
            passed=has_crud_table and has_c and has_r and has_u and has_d,
            details=f"Checks CRUD: DB Table={has_crud_table}, POST={has_c}, GET={has_r}, PUT={has_u}, DELETE={has_d}"
        ))

        # 3. Analytics Flow Checks
        # Verify admin dashboard and metrics endpoints
        has_admin_role = "Admin" in auth_roles
        has_analytics_ui = any("analytics" in page.name.lower() or "dashboard" in page.name.lower() for page in ui.pages)
        has_analytics_api = any("analytics" in ep.path.lower() or "users" in ep.path.lower() for ep in api.endpoints)

        checks.append(RuntimeCheck(
            flow="Analytics Flow",
            component="Admin & Dashboard Integration",
            passed=has_admin_role and has_analytics_ui and has_analytics_api,
            details=f"Analytics: Admin Role={has_admin_role}, UI Dashboard={has_analytics_ui}, API Analytics={has_analytics_api}"
        ))

        # 4. Premium Flow Checks
        # Verify subscription schemas and premium rules gating
        has_sub_table = "subscriptions" in db_tables
        has_premium_rule = len(business.premium_gates) > 0
        has_billing_ui = any("billing" in page.path.lower() for page in ui.pages)

        checks.append(RuntimeCheck(
            flow="Premium Flow",
            component="Subscription Gating",
            passed=has_sub_table and has_premium_rule and has_billing_ui,
            details=f"Premium Gating: Sub Table={has_sub_table}, Gating Rule={has_premium_rule}, Billing UI={has_billing_ui}"
        ))

        # Overall verifications check
        passed = all(check.passed for check in checks if "Login" in check.flow) # Critical requirement: login flow must pass

        return RuntimeReport(
            passed=passed,
            checks=checks
        )
