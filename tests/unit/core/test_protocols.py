import pytest

from nexus_cove.core.models import Task
from nexus_cove.core.protocols import decode_message, encode_message, task_to_payload


def test_protocol_round_trip() -> None:
    raw = encode_message(
        "task_assign", recipient="Aegis", task=task_to_payload(Task(prompt="hello"))
    )
    decoded = decode_message(raw)
    assert decoded["action"] == "task_assign"
    assert decoded["recipient"] == "Aegis"


def test_protocol_rejects_missing_version() -> None:
    with pytest.raises(ValueError):
        decode_message('{"action":"ping"}')
