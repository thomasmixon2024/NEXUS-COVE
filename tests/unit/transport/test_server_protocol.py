import pytest

from nexus_cove.core.protocols import decode_message, encode_message


def test_error_messages_are_structured() -> None:
    raw = encode_message("error", error="bad payload")
    assert decode_message(raw)["error"] == "bad payload"


def test_unknown_protocol_version_is_rejected() -> None:
    with pytest.raises(ValueError):
        decode_message('{"version":999,"action":"ping"}')
