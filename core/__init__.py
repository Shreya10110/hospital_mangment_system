import logging
from pathlib import Path

def logger(name: str) -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)
    instance = logging.getLogger(name)
    if not instance.handlers:
        instance.setLevel(logging.INFO)
        handler = logging.FileHandler("logs/debug.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        instance.addHandler(handler)
    return instance
