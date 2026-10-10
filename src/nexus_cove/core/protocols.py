from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from .models import Task, TaskResult

PROTOCOL_VERSION = 1


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def encode_message(action: str, **payload: Any) -> str:
    return json.dumps(
        {"version": PROTOCOL_VERSION, "action": action, **payload}, default=_json_default
    )


def decode_message(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")
    if data.get("version") != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {data.get('version')!r}")
    action = data.get("action")
    if not isinstance(action, str) or not action:
        raise ValueError("Message action is required")
    return data


def task_to_payload(task: Task) -> dict[str, Any]:
    data = asdict(task)
    data["required_capabilities"] = sorted(task.required_capabilities)
    return data


def result_to_payload(result: TaskResult) -> dict[str, Any]:
    return asdict(result)
