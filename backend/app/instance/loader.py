from dataclasses import dataclass, field
from pathlib import Path

import yaml


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

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    instance_raw = raw.get("instance", {})
    _instance_config = InstanceConfig(
        name=instance_raw.get("name", "LifeHub"),
        description=instance_raw.get("description", ""),
        modules=raw.get("modules", {}),
        extensions=raw.get("extensions", {}),
    )
    return _instance_config


def get_instance_config() -> InstanceConfig:
    """Restituisce la configurazione già caricata. Lancia se non ancora caricata."""
    if _instance_config is None:
        raise RuntimeError("Instance config not loaded — call load_instance_config() first")
    return _instance_config
