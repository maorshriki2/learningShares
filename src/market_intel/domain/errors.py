class DomainError(Exception):
    """Base class for domain-level errors."""


class NotFoundError(DomainError):
    """Requested resource does not exist."""


class ValidationError(DomainError):
    """Domain validation failed."""


class RateLimitedError(DomainError):
    """Upstream rate limit encountered."""


class ProviderUnavailableError(DomainError):
    """Market or data provider unavailable."""
