"""Deterministic local embedding adapter used when no hosted embedding model is configured."""
import re
def embed(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z0-9]+", text) if len(token) > 2}
