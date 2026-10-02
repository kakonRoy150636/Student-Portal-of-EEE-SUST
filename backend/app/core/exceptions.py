class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None):
        self.message = message
        self.status_code = status_code
        # Machine-readable discriminator. The message is for humans and may be
        # reworded at any time; the client keys off this instead.
        self.code = code
        super().__init__(message)

class UnauthorizedException(DomainException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=401)

class ForbiddenException(DomainException):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message=message, status_code=403)

class ResourceConflictException(DomainException):
    def __init__(self, message: str = "Conflict detected"):
        super().__init__(message=message, status_code=409)

class NotFoundException(DomainException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)

class ValidationException(DomainException):
    """Request understood but rejected on domain grounds (422)."""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(message=message, status_code=422)

class TooManyRequestsException(DomainException):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message=message, status_code=429)

class PasswordChangeRequiredException(DomainException):
    """Account authenticated, but the temporary password must be replaced first."""

    def __init__(
        self,
        message: str = "You must change your password before continuing.",
    ):
        super().__init__(message=message, status_code=403, code="password_change_required")


class MfaEnrollmentRequiredException(DomainException):
    """Privileged account that has not enrolled its second factor yet."""

    def __init__(
        self,
        message: str = "Enrol a second factor to continue.",
    ):
        super().__init__(message=message, status_code=403, code="mfa_enrollment_required")
