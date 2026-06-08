from __future__ import annotations

import time
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from modules.intent.extractor import extract_intent, IntentResult
from modules.architecture.generator import generate_architecture, ArchitectureResult
from modules.schema.database_generator import generate_database, DatabaseSchema
from modules.schema.api_generator import generate_api, ApiSchema
from modules.schema.ui_generator import generate_ui, UiSchema
from modules.schema.auth_generator import generate_auth, AuthSchema
from modules.schema.business_generator import generate_business_rules, BusinessSchema
from modules.validation.engine import ValidationEngine, ValidationReport
from modules.repair.engine import RepairEngine, RepairReport
from modules.runtime.verifier import RuntimeVerifier, RuntimeReport

class CompilationMetrics(BaseModel):
    total_time_ms: int
    repair_attempts: int
    success_rate: float = 1.0

class CompileResult(BaseModel):
    prompt: str
    intent: IntentResult
    architecture: ArchitectureResult
    database: DatabaseSchema
    api: ApiSchema
    ui: UiSchema
    auth: AuthSchema
    business: BusinessSchema
    validation: ValidationReport
    repair: Optional[RepairReport] = None
    runtime: RuntimeReport
    metrics: CompilationMetrics

class AppCompiler:
    def __init__(self) -> None:
        self.validator = ValidationEngine()
        self.repair_engine = RepairEngine()
        self.verifier = RuntimeVerifier()

    def compile(self, prompt: str) -> CompileResult:
        start_time = time.time()
        
        # 1. Intent Extraction
        intent = extract_intent(prompt)
        
        # 2. Architecture Generation
        architecture = generate_architecture(intent)
        
        # 3. Schema Generation
        database = generate_database(architecture)
        api = generate_api(architecture)
        ui = generate_ui(architecture)
        auth = generate_auth(architecture)
        business = generate_business_rules(architecture)
        
        # 4. Validation
        validation = self.validator.validate(architecture, database, api, ui, auth, business)
        
        # 5. Repair Loop
        repair_attempts = 0
        repair_report = None
        
        while not validation.valid and repair_attempts < 3:
            repair_report = self.repair_engine.repair(
                validation.errors,
                repair_attempts,
                database,
                api,
                ui,
                auth,
                business
            )
            repair_attempts += 1
            # Re-validate after repair
            validation = self.validator.validate(architecture, database, api, ui, auth, business)

        # 6. Runtime Verification
        runtime = self.verifier.verify(architecture, database, api, ui, auth, business)
        
        # 7. Metrics
        total_time_ms = int((time.time() - start_time) * 1000)
        metrics = CompilationMetrics(
            total_time_ms=total_time_ms,
            repair_attempts=repair_attempts,
            success_rate=1.0 if runtime.passed else 0.0
        )
        
        return CompileResult(
            prompt=prompt,
            intent=intent,
            architecture=architecture,
            database=database,
            api=api,
            ui=ui,
            auth=auth,
            business=business,
            validation=validation,
            repair=repair_report,
            runtime=runtime,
            metrics=metrics
        )
