class CoveError(Exception):
    """Base exception for expected Cove application errors."""


class ProtocolError(CoveError):
    """Raised when a transport message is invalid."""


class AgentUnavailable(CoveError):
    """Raised when no registered agent can accept a task."""
