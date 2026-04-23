import json
from typing import Any


def parse_filters(raw_filter: str | None) -> dict[str, Any]:
    if not raw_filter:
        return {}
    try:
        loaded = json.loads(raw_filter)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}

