from app.instance.loader import get_instance_config
from app.modules.base import DomainModule, ModuleRegistry
from app.modules.search import search_events, search_knowledge, search_people, search_places


class SearchableModule(DomainModule):
    search_fn = None

    async def search(self, db, query: str, limit: int, fuzzy: bool = False) -> list[dict]:
        if not self.searchable or not self.search_fn:
            return []
        return await self.search_fn(db, query, limit, fuzzy=fuzzy)


def build_module_registry() -> ModuleRegistry:
    enabled = get_instance_config().modules
    registry = ModuleRegistry()
    registry.register(SearchableModule("people", "People", "Manage people, contacts and relationships", enabled=enabled.get("people", False)))
    registry.modules["people"].search_fn = search_people
    registry.register(SearchableModule("places", "Places", "Manage locations and visits", requires=("maps",), enabled=enabled.get("places", False)))
    registry.modules["places"].search_fn = search_places
    registry.register(SearchableModule("events", "Events", "Manage events and timeline", enabled=enabled.get("events", False)))
    registry.modules["events"].search_fn = search_events
    registry.register(SearchableModule("knowledge", "Knowledge", "Manage flexible knowledge items", enabled=enabled.get("knowledge", False)))
    registry.modules["knowledge"].search_fn = search_knowledge
    registry.register(SearchableModule("buildings", "Buildings", "Reusable buildings example", requires=("maps",), uses=("core", "meta", "shared", "people"), enabled=enabled.get("buildings", False)))
    return registry
