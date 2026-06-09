from __future__ import annotations

import grpc
from concurrent import futures
import time
from cri.grpc_runtime import interrupt_pb2
from cri.grpc_runtime import interrupt_pb2_grpc
from cri.rollback_engine.coordinator import RollbackCoordinator

class InterruptServiceServicer(interrupt_pb2_grpc.InterruptServiceServicer):
    def __init__(self) -> None:
        self.paused_agents: set[str] = set()
        self.coordinator = RollbackCoordinator()
        # Mock active checkpoint/backup mapping for testing
        self.checkpoint_backups: dict[str, dict[str, str]] = {}

    def Pause(self, request: interrupt_pb2.PauseRequest, context: grpc.ServicerContext) -> interrupt_pb2.PauseResponse:
        agent_id = request.agent_id
        if agent_id in self.paused_agents:
            return interrupt_pb2.PauseResponse(
                status="ALREADY_PAUSED",
                message=f"Agent {agent_id} is already paused."
            )
        self.paused_agents.add(agent_id)
        print(f"Agent {agent_id} PAUSED. Reason: {request.reason}")
        return interrupt_pb2.PauseResponse(
            status="PAUSED",
            message=f"Agent {agent_id} has been successfully paused."
        )

    def Resume(self, request: interrupt_pb2.ResumeRequest, context: grpc.ServicerContext) -> interrupt_pb2.ResumeResponse:
        agent_id = request.agent_id
        if agent_id in self.paused_agents:
            self.paused_agents.remove(agent_id)
            print(f"Agent {agent_id} RESUMED.")
            return interrupt_pb2.ResumeResponse(
                status="RUNNING",
                message=f"Agent {agent_id} has been resumed."
            )
        return interrupt_pb2.ResumeResponse(
            status="RUNNING",
            message=f"Agent {agent_id} was not paused; already running."
        )

    def TriggerRollback(self, request: interrupt_pb2.RollbackRequest, context: grpc.ServicerContext) -> interrupt_pb2.RollbackResponse:
        checkpoint_id = request.checkpoint_id
        agent_id = request.agent_id
        
        # Look up file backups for this checkpoint
        backup_map = self.checkpoint_backups.get(checkpoint_id, {})
        if not backup_map:
            # Fallback/mock files for testing if map is empty
            backup_map = {}

        try:
            restored = self.coordinator.restore_files(checkpoint_id, backup_map)
            print(f"Rollback triggered for checkpoint {checkpoint_id}. Restored {len(restored)} files.")
            
            # Resume agent automatically after successful rollback repair
            if agent_id in self.paused_agents:
                self.paused_agents.remove(agent_id)

            return interrupt_pb2.RollbackResponse(
                status="SUCCESS",
                message=f"Successfully rolled back agent {agent_id} state.",
                restored_files=restored
            )
        except Exception as exc:
            return interrupt_pb2.RollbackResponse(
                status="FAILED",
                message=f"Rollback failed: {exc}",
                restored_files=[]
            )

def serve(port: int = 50051) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    servicer = InterruptServiceServicer()
    interrupt_pb2_grpc.add_InterruptServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC Interrupt Service started on port {port}.")
    return server

if __name__ == "__main__":
    server = serve()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
