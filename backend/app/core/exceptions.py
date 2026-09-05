class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
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
