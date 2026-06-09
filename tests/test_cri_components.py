"""
tests/test_cri_components.py
Unit tests for CRI Phase 3-12 components.
Runs entirely offline — no live services required.
"""
from __future__ import annotations

import sys
import os

# Ensure workspace root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Phase 3: Semantic State & DAG ──────────────────────────────────────────

def test_state_hash_is_deterministic():
    from cri.semantic_state.state import AgentState, semantic_state_hash
    state = AgentState(current_goal="test", current_plan="plan A", constraints=["no delete"])
    h1 = semantic_state_hash(state)
    h2 = semantic_state_hash(state)
    assert h1 == h2, "Same state must produce same hash"


def test_state_hash_changes_with_goal():
    from cri.semantic_state.state import AgentState, semantic_state_hash
    s1 = AgentState(current_goal="goal-A")
    s2 = AgentState(current_goal="goal-B")
    assert semantic_state_hash(s1) != semantic_state_hash(s2)


def test_dag_create_and_restore():
    from cri.checkpoint_engine.dag import CheckpointDAG
    from cri.semantic_state.state import AgentState
    dag = CheckpointDAG()
    state = AgentState(current_goal="build feature X")
    node = dag.create_checkpoint(state)
    assert node.checkpoint_id in dag.nodes
    restored = dag.restore_checkpoint(node.checkpoint_id)
    assert restored is not None
    assert restored.current_goal == "build feature X"


def test_dag_lineage():
    from cri.checkpoint_engine.dag import CheckpointDAG
    from cri.semantic_state.state import AgentState
    dag = CheckpointDAG()
    s1 = dag.create_checkpoint(AgentState(current_goal="step 1"))
    s2 = dag.create_checkpoint(AgentState(current_goal="step 2"))
    lineage = dag.get_lineage(s2.checkpoint_id)
    assert len(lineage) == 2
    assert lineage[0] == s2.checkpoint_id


# ── Phase 4: Belief Store ──────────────────────────────────────────────────

def test_belief_store_embedding_fallback():
    """Verifies the BeliefStore fallback embeddings are consistent."""
    from cri.belief_engine.store import BeliefStore
    store = BeliefStore()
    store.use_fallback_embeddings = True
    store.model = None
    v1 = store.get_embedding("auth services use oauth")
    v2 = store.get_embedding("auth services use oauth")
    assert v1 == v2, "Fallback embeddings must be deterministic"
    assert len(v1) == 384


def test_belief_store_embedding_is_vector():
    from cri.belief_engine.store import BeliefStore
    store = BeliefStore()
    store.use_fallback_embeddings = True
    store.model = None
    v = store.get_embedding("test belief text")
    assert isinstance(v, list)
    assert all(isinstance(x, float) for x in v)


# ── Phase 5: NLI Contradiction Classifier ─────────────────────────────────

def test_nli_heuristic_detects_rm():
    from cri.verification_runtime.nli import NLIContradictionClassifier
    clf = NLIContradictionClassifier()
    clf.use_fallback = True
    clf.classifier = None
    score = clf._heuristic_check(
        "rm -rf /tmp/data",
        "Critical data must never be deleted without approval"
    )
    assert score > 0.0, "Should flag rm command"


def test_nli_heuristic_passes_safe_action():
    from cri.verification_runtime.nli import NLIContradictionClassifier
    clf = NLIContradictionClassifier()
    clf.use_fallback = True
    clf.classifier = None
    score = clf._heuristic_check(
        "echo hello",
        "Auth services should use OAuth2"
    )
    assert score < 0.7, "echo hello should not strongly contradict OAuth belief"


# ── Phase 6: Rollback Coordinator ─────────────────────────────────────────

def test_rollback_coordinator_backup_and_restore(tmp_path):
    from cri.rollback_engine.coordinator import RollbackCoordinator
    # Create a temp file to backup
    src = tmp_path / "test_file.py"
    src.write_text("x = 1", encoding="utf-8")

    coord = RollbackCoordinator(backup_dir=str(tmp_path / ".backups"))
    backup_map = coord.backup_files("ckpt-001", [str(src)])
    assert len(backup_map) == 1

    # Modify original
    src.write_text("x = 999", encoding="utf-8")
    assert src.read_text() == "x = 999"

    # Restore
    restored = coord.restore_files("ckpt-001", backup_map)
    assert len(restored) == 1
    assert src.read_text() == "x = 1"


# ── Phase 10: Memory Arbitration ──────────────────────────────────────────

def test_episodic_memory_record_and_retrieve(tmp_path, monkeypatch):
    import cri.agent_runtime.memory as mem_mod
    monkeypatch.setattr(mem_mod, "_MEMORY_FILE", tmp_path / "mem.jsonl")
    from cri.agent_runtime.memory import EpisodicMemory
    mem = EpisodicMemory()
    mem.record("run echo hello", "success")
    mem.record("rm -rf /", "blocked")
    recent = mem.recent(5)
    assert len(recent) == 2
    assert recent[0]["step"] == "run echo hello"


def test_semantic_memory_retrieves_relevant_rule():
    from cri.agent_runtime.memory import SemanticMemory
    sm = SemanticMemory()
    results = sm.retrieve("sandbox execution for high risk commands")
    texts = [r["rule"] for r in results]
    assert any("sandbox" in t.lower() or "HIGH" in t for t in texts)


# ── Phase 11: Context Governance ──────────────────────────────────────────

def test_context_governor_prunes_to_budget():
    from cri.agent_runtime.governance import ContextGovernorEngine
    gov = ContextGovernorEngine(token_budget=50)
    items = [{"content": "word " * 30, "priority": 0.9, "tag": "high"},
             {"content": "word " * 30, "priority": 0.1, "tag": "low"}]
    result = gov.govern(items)
    assert result["total_tokens"] <= 50 or result["items_dropped"] > 0


def test_context_governor_stable_for_small_context():
    from cri.agent_runtime.governance import ContextGovernorEngine
    gov = ContextGovernorEngine(token_budget=1000)
    items = [{"content": "Short item.", "priority": 0.8, "tag": "task"}]
    result = gov.govern(items)
    assert result["stable"] is True


# ── Phase 1: Classifiers ──────────────────────────────────────────────────

def test_classifier_flags_rm():
    from cri.runtime_core.classifiers import classify_shell
    result = classify_shell("rm -rf /")
    assert result["risk"] == "HIGH"


def test_classifier_passes_echo():
    from cri.runtime_core.classifiers import classify_shell
    result = classify_shell("echo hello")
    assert result["risk"] == "LOW"


def test_ast_classifier_flags_os_import():
    from cri.runtime_core.classifiers import ActionClassifier
    clf = ActionClassifier()
    result = clf.classify("import os\nos.remove('/etc/passwd')")
    assert result["risk"] == "HIGH"
