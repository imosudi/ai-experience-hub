class MuseSparkError(Exception):
    """Base exception class for Muse Spark Explorer."""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status'] = self.status_code
        return rv


class SDKConnectionError(MuseSparkError):
    """Raised when there is a connection timeout or failure to contact the Muse Spark API."""
    def __init__(self, message="Failed to connect to Muse Spark API", status_code=503, payload=None):
        super().__init__(message, status_code, payload)


class AuthenticationError(MuseSparkError):
    """Raised when API credentials or session tokens are invalid or expired."""
    def __init__(self, message="Authentication failed", status_code=401, payload=None):
        super().__init__(message, status_code, payload)


class RateLimitError(MuseSparkError):
    """Raised when request limits are exceeded."""
    def __init__(self, message="Rate limit exceeded", status_code=429, payload=None):
        super().__init__(message, status_code, payload)


class InvalidInputError(MuseSparkError):
    """Raised when input parameters (e.g., negative temperature, too large upload, invalid URL) are invalid."""
    def __init__(self, message="Invalid input parameters", status_code=400, payload=None):
        super().__init__(message, status_code, payload)
