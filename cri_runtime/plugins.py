"""Plugin and extension SDK primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class RuntimeExtension(Protocol):
    name: str
    version: str

    def register(self, registry: "PluginRegistry") -> None:
        ...


Hook = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class PluginDescriptor:
    name: str
    version: str
    capabilities: tuple[str, ...] = ()


@dataclass
class PluginRegistry:
    plugins: dict[str, PluginDescriptor] = field(default_factory=dict)
    hooks: dict[str, list[Hook]] = field(default_factory=dict)

    def register_plugin(self, descriptor: PluginDescriptor) -> None:
        self.plugins[descriptor.name] = descriptor

    def register_hook(self, hook_name: str, hook: Hook) -> None:
        self.hooks.setdefault(hook_name, []).append(hook)

    def run_hooks(self, hook_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        for hook in self.hooks.get(hook_name, []):
            result = hook(result)
        return result

    def load_extension(self, extension: RuntimeExtension) -> None:
        self.register_plugin(
            PluginDescriptor(
                name=extension.name,
                version=extension.version,
                capabilities=("extension",),
            )
        )
        extension.register(self)

