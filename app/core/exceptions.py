class EmailConflictError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


class AccountLockedError(Exception):
    """Exception raised for locked account (HTTP 423)."""

    pass


class InvalidCredentialsError(Exception):
    """Generic exception raised for invalid login attempt"""

    pass


class EmailNotVerifiedError(Exception):
    """Exception raised when a user attempts to login without verifying their email."""

    pass
