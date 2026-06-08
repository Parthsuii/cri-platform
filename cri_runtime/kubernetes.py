from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KubernetesManifest:
    path: str
    kind: str
    name: str


class KubernetesExecutionFabric:
    def __init__(self, manifest_dir: str = "k8s") -> None:
        self.manifest_dir = Path(manifest_dir)

    def manifests(self) -> list[KubernetesManifest]:
        return [
            KubernetesManifest("k8s/namespace.yaml", "Namespace", "cri-runtime"),
            KubernetesManifest("k8s/configmap.yaml", "ConfigMap", "cri-runtime-config"),
            KubernetesManifest("k8s/runtime-job.yaml", "Job", "cri-runtime-agent"),
            KubernetesManifest("k8s/serviceaccount.yaml", "ServiceAccount", "cri-runtime-runner"),
        ]

    def plan(self) -> dict[str, Any]:
        return {
            "fabric": "kubernetes",
            "namespace": "cri-runtime",
            "apply_order": [asdict(manifest) for manifest in self.manifests()],
            "entrypoint": "python main.py --cognition-os \"run echo from-kubernetes\"",
        }
