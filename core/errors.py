"""Custom exceptions for the RPA application."""


class RPAError(Exception):
    """Base exception for all RPA errors."""

    pass


class TransientError(RPAError):
    """
    Recoverable error that should be retried.

    Examples:
    - Temporary network issues
    - Portal timeout (not consistently)
    - Stale element references
    """

    pass


class ValidationError(RPAError):
    """
    Data validation error that should NOT be retried.

    Examples:
    - Missing required fields
    - Invalid date formats
    - Business rule violations
    """

    pass


class PortalChangedError(RPAError):
    """
    Portal structure has changed, requiring manual intervention.

    Examples:
    - Selector no longer matches
    - Page layout changed
    - New authentication flow
    """

    pass


class PortalBusinessError(RPAError):
    """
    Portal returned a business error (not a technical failure).

    Examples:
    - Invalid member ID
    - No coverage found
    - Service type not supported for this payer
    """

    pass

