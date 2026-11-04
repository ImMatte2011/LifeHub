from dataclasses import dataclass


@dataclass(frozen=True)
class Extension:
    name: str
    kind: str
    description: str
    dependencies: tuple[str, ...] = ()


EXTENSIONS = {
    "postgis": Extension("postgis", "atomic", "PostgreSQL spatial types and indexes"),
    "leaflet": Extension("leaflet", "atomic", "Interactive map rendering in the browser"),
    "openstreetmap": Extension("openstreetmap", "atomic", "OpenStreetMap tile provider"),
    "pg_trgm": Extension("pg_trgm", "atomic", "PostgreSQL trigram similarity search"),
    "maps": Extension("maps", "capability", "Complete map capability", ("postgis", "leaflet", "openstreetmap")),
}


class ExtensionManager:
    """Resolves requested capabilities into independent, verifiable components."""

    def __init__(self, configured: dict[str, bool]):
        self.configured = configured
        self.requested: set[str] = {name for name, enabled in configured.items() if enabled}
        self.required = set(self.requested)
        pending = list(self.requested)
        while pending:
            item = EXTENSIONS.get(pending.pop())
            if item:
                for dependency in item.dependencies:
                    if dependency not in self.required:
                        self.required.add(dependency)
                        pending.append(dependency)
        self.available: dict[str, bool] = {"leaflet": True, "openstreetmap": True}

    async def initialize(self, connection) -> None:
        for name in sorted(self.required):
            if name == "postgis":
                try:
                    async with connection.begin_nested():
                        await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
                        await connection.exec_driver_sql("ALTER TABLE places.places ADD COLUMN IF NOT EXISTS geom geography(Point, 4326)")
                        await connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_places_geom_gist ON places.places USING GIST (geom)")
                        await connection.exec_driver_sql("UPDATE places.places SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL")
                    self.available[name] = True
                except Exception:
                    self.available[name] = False
            elif name == "pg_trgm":
                try:
                    async with connection.begin_nested():
                        await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    self.available[name] = True
                except Exception:
                    self.available[name] = False
            elif name in {"leaflet", "openstreetmap"}:
                self.available[name] = True

    def is_available(self, name: str) -> bool:
        spec = EXTENSIONS.get(name)
        if not spec or name not in self.required:
            return False
        if spec.kind == "capability":
            return all(self.available.get(dependency, False) for dependency in spec.dependencies)
        return self.available.get(name, False)

    def status(self) -> list[dict]:
        return [
            {"name": item.name, "kind": item.kind, "description": item.description,
             "enabled": name in self.required, "requested": name in self.requested, "available": self.is_available(name),
             "requires": list(item.dependencies)}
            for name, item in EXTENSIONS.items()
        ]
