"""HTTP router package.

The feature routers live here.  `router` remains the aggregate imported by the
application so the original API URLs stay stable while endpoints are migrated
feature-by-feature from the compatibility module.
"""
from core.apis.legacy_routes import router

__all__ = ["router"]
