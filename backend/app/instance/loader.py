from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError


@dataclass
class InstanceConfig:
    name: str = "LifeHub"
    description: str = ""
    modules: dict[str, bool] = field(default_factory=dict)
    extensions: dict[str, bool] = field(default_factory=dict)


_instance_config: InstanceConfig | None = None


def load_instance_config(path: str) -> InstanceConfig:
    """Legge instance.yaml e restituisce la configurazione."""
    global _instance_config

    config_path = Path(path)
    if not config_path.exists():
        _instance_config = InstanceConfig()
        return _instance_config

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw = raw or {}
    instance_raw = raw.get("instance", {}) or {}
    modules = raw.get("modules", {}) or {}
    extensions = raw.get("extensions", {}) or {}
    if not isinstance(modules, dict) or not isinstance(extensions, dict):
        raise ValueError("instance.yaml modules and extensions must be mappings")
    if any(not isinstance(value, bool) for value in [*modules.values(), *extensions.values()]):
        raise ValueError("instance.yaml module and extension flags must be booleans")
    _instance_config = InstanceConfig(
        name=instance_raw.get("name", "LifeHub"),
        description=instance_raw.get("description", ""),
        modules=modules,
        extensions=extensions,
    )
    return _instance_config


def get_instance_config() -> InstanceConfig:
    """Restituisce la configurazione già caricata. Lancia se non ancora caricata."""
    if _instance_config is None:
        raise RuntimeError("Instance config not loaded — call load_instance_config() first")
    return _instance_config
