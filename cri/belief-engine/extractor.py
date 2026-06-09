from __future__ import annotations

import json
from pydantic import BaseModel, Field
from typing import Any
from modules.utils.llm import call_llm_structured
from .parser import scan_repository
from .store import BeliefStore

class ExtractedBelief(BaseModel):
    belief: str = Field(description="Statement of the project rule or constraint")
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    category: str = Field(description="Category of the rule, e.g., security, architecture, dependency")

class BeliefExtractionList(BaseModel):
    beliefs: list[ExtractedBelief]

class BeliefExtractor:
    def __init__(self, store: BeliefStore | None = None) -> None:
        self.store = store or BeliefStore()

    def run_heuristics(self, findings: list[dict[str, Any]]) -> list[ExtractedBelief]:
        """Generate deterministic/heuristic beliefs from AST scan findings."""
        beliefs = []
        
        # 1. Check for web frameworks and execution
        has_web = False
        has_exec = False
        for file_info in findings:
            imports = file_info.get("imports", [])
            calls = file_info.get("calls", [])
            if any(x in imports for x in {"fastapi", "flask", "django"}):
                has_web = True
            if any(x in imports for x in {"subprocess", "os"}) or any(y in calls for y in {"system", "run", "Popen"}):
                has_exec = True

        if has_web and has_exec:
            beliefs.append(ExtractedBelief(
                belief="Web entry points should avoid executing raw shell commands directly to prevent injection.",
                confidence=0.95,
                category="security"
            ))

        # 2. Check for database operations
        has_sql = False
        for file_info in findings:
            calls = file_info.get("calls", [])
            if any(c in {"execute", "cursor", "SQL"} for c in calls):
                has_sql = True
                
        if has_sql:
            beliefs.append(ExtractedBelief(
                belief="Database interactions should prefer parameterized queries or structured ORM access.",
                confidence=0.90,
                category="database"
            ))

        # 3. Code isolation rule
        beliefs.append(ExtractedBelief(
            belief="Critical system commands and administrative functions must run within restricted container sandbox environments.",
            confidence=0.98,
            category="security"
        ))
        
        return beliefs

    def extract_and_store(self, repo_path: str) -> list[dict[str, Any]]:
        findings = scan_repository(repo_path)
        
        # Try LLM-based extraction first
        system_prompt = (
            "You are a software architect learning project beliefs/rules from AST code summaries. "
            "Formulate 3-5 rules about security, dependency management, API design, or coding standards. "
            "Return only the rules."
        )
        user_message = f"Here are the AST parser findings from the project files:\n{json.dumps(findings[:10])}"
        
        extracted_list = call_llm_structured(
            messages=[{"role": "user", "content": user_message}],
            response_model=BeliefExtractionList,
            system_prompt=system_prompt
        )
        
        beliefs = []
        if extracted_list and extracted_list.beliefs:
            beliefs = extracted_list.beliefs
        else:
            # Fall back to heuristic rule generation if LLM is rate-limited or fails
            beliefs = self.run_heuristics(findings)
            
        stored = []
        for idx, b in enumerate(beliefs):
            belief_id = f"belief-rule-{idx}"
            success = self.store.upsert_belief(
                belief_id=belief_id,
                belief_text=b.belief,
                confidence=b.confidence,
                metadata={"category": b.category}
            )
            if success:
                stored.append({
                    "belief_id": belief_id,
                    "belief": b.belief,
                    "confidence": b.confidence,
                    "category": b.category
                })
        return stored
