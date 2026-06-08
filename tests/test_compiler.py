from __future__ import annotations

import pytest
from orchestrator.compiler import AppCompiler
from modules.intent.extractor import extract_intent
from modules.architecture.generator import generate_architecture
from modules.schema.database_generator import generate_database
from modules.schema.api_generator import generate_api
from modules.schema.ui_generator import generate_ui
from modules.schema.auth_generator import generate_auth
from modules.schema.business_generator import generate_business_rules
from modules.validation.engine import ValidationEngine, ValidationError
from modules.repair.engine import RepairEngine
from modules.runtime.verifier import RuntimeVerifier

def test_compiler_pipeline_crm() -> None:
    compiler = AppCompiler()
    result = compiler.compile("Build a CRM with login and contacts and admin analytics")
    
    assert result.intent.app_type == "crm"
    assert "login" in result.intent.features or "contacts" in result.intent.features
    assert "User" in result.architecture.entities
    assert "Contact" in result.architecture.entities
    
    # Assert database schema
    tables = {t.name for t in result.database.tables}
    assert "users" in tables
    assert "contacts" in tables

    # Assert API schema
    paths = {ep.path for ep in result.api.endpoints}
    assert "/api/auth/login" in paths
    assert "/api/contacts" in paths

    # Assert UI schema
    pages = {p.path for p in result.ui.pages}
    assert "/login" in pages
    assert "/contacts" in pages

    # Assert Auth schema
    roles = {r.name for r in result.auth.roles}
    assert "Admin" in roles
    assert "User" in roles

    # Validation should pass
    assert result.validation.valid is True
    assert result.runtime.passed is True

def test_validation_and_repair_missing_users_table() -> None:
    intent = extract_intent("Build CRM with contacts")
    architecture = generate_architecture(intent)
    
    # Intentionally corrupt the schemas to trigger validation failures
    database = generate_database(architecture)
    # Remove users table to trigger runtime & login flow error
    database.tables = [t for t in database.tables if t.name != "users"]
    
    api = generate_api(architecture)
    ui = generate_ui(architecture)
    auth = generate_auth(architecture)
    business = generate_business_rules(architecture)
    
    validator = ValidationEngine()
    report = validator.validate(architecture, database, api, ui, auth, business)
    
    # It should detect errors
    assert report.valid is False
    assert any("users" in err.message or "Login flow" in err.message for err in report.errors)
    
    # Repair
    repair_engine = RepairEngine()
    rep_report = repair_engine.repair(report.errors, 0, database, api, ui, auth, business)
    
    assert rep_report.success is True
    assert any("users" in step.action_taken for step in rep_report.steps)
    
    # Verify again
    new_report = validator.validate(architecture, database, api, ui, auth, business)
    assert new_report.valid is True

def test_validation_and_repair_missing_column() -> None:
    intent = extract_intent("Build CRM with contacts")
    architecture = generate_architecture(intent)
    
    database = generate_database(architecture)
    api = generate_api(architecture)
    # Add a custom parameter in API request body that doesn't exist in DB fields to trigger cross-layer mismatch
    for ep in api.endpoints:
        if ep.path == "/api/contacts" and ep.method == "POST":
            ep.request_body["unknown_field"] = "string"
            
    ui = generate_ui(architecture)
    auth = generate_auth(architecture)
    business = generate_business_rules(architecture)
    
    validator = ValidationEngine()
    report = validator.validate(architecture, database, api, ui, auth, business)
    
    assert report.valid is False
    assert any("unknown_field" in err.message for err in report.errors)
    
    # Repair
    repair_engine = RepairEngine()
    rep_report = repair_engine.repair(report.errors, 0, database, api, ui, auth, business)
    assert rep_report.success is True
    
    # Verify again
    new_report = validator.validate(architecture, database, api, ui, auth, business)
    assert new_report.valid is True
