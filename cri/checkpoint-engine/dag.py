from __future__ import annotations

import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from cri.semantic_state.state import AgentState, semantic_state_hash

class CheckpointNode(BaseModel):
    checkpoint_id: str
    state: AgentState
    parent_ids: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)

class CheckpointDAG(BaseModel):
    nodes: Dict[str, CheckpointNode] = Field(default_factory=dict)
    active_checkpoint_id: Optional[str] = None

    def create_checkpoint(self, state: AgentState, parent_ids: List[str] | None = None) -> CheckpointNode:
        ch_id = semantic_state_hash(state)
        
        # If parents not supplied, use currently active node
        parents = parent_ids if parent_ids is not None else ([] if not self.active_checkpoint_id else [self.active_checkpoint_id])
        
        node = CheckpointNode(
            checkpoint_id=ch_id,
            state=state.model_copy(deep=True),
            parent_ids=parents
        )
        self.nodes[ch_id] = node
        self.active_checkpoint_id = ch_id
        return node

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointNode]:
        return self.nodes.get(checkpoint_id)

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[AgentState]:
        node = self.get_checkpoint(checkpoint_id)
        if node:
            self.active_checkpoint_id = checkpoint_id
            return node.state.model_copy(deep=True)
        return None

    def get_lineage(self, checkpoint_id: str) -> List[str]:
        lineage = []
        curr = self.get_checkpoint(checkpoint_id)
        while curr:
            lineage.append(curr.checkpoint_id)
            if curr.parent_ids:
                # Traverse primary parent
                curr = self.get_checkpoint(curr.parent_ids[0])
            else:
                curr = None
        return lineage
