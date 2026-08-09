"""Database-related FastAPI dependencies.

Re-exports the request-scoped session dependency from the infrastructure layer
so API modules depend on ``app.api.dependencies`` rather than reaching across
into ``infrastructure`` directly.
"""

from __future__ import annotations

from infrastructure.database.session import get_db

__all__ = ["get_db"]
