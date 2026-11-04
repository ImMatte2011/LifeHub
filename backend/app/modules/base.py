from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DomainModule:
    name: str
    display_name: str
    description: str
    requires: tuple[str, ...] = ()
    uses: tuple[str, ...] = ("core", "meta", "shared")
    enabled: bool = False
    searchable: bool = True

    async def search(self, db: AsyncSession, query: str, limit: int, fuzzy: bool = False) -> list[dict]:
        return []


@dataclass
class ModuleRegistry:
    modules: dict[str, DomainModule] = field(default_factory=dict)

    def register(self, module: DomainModule) -> None:
        if module.name in self.modules:
            raise ValueError(f"Duplicate module: {module.name}")
        self.modules[module.name] = module

    def status(self, extensions) -> list[dict]:
        return [{"name": module.name, "enabled": module.enabled,
                 "available": module.enabled and all(extensions.is_available(name) for name in module.requires),
                 "requires": list(module.requires), "uses": list(module.uses)}
                for module in self.modules.values()]
