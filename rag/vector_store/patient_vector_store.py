"""Patient-filtered store contract. Persistence is provided by `services.rag_service`."""
from services.rag_service import retrieve
__all__ = ["retrieve"]
