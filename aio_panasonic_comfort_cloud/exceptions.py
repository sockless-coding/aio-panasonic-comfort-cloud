class Error(Exception):
    pass


class LoginError(Error):
    pass


class RequestError(Error):
    pass


class ResponseError(Error):
    pass

class DeviceIsNotReadyError(Error):
    """Raised when a device is not ready (features/parameters not yet loaded)."""
    pass


class MFARequiredError(Error):
    """Raised when multi-factor authentication is required during login."""

    def __init__(self, mfa_token: str = None):
        self.mfa_token = mfa_token
        super().__init__("Multi-factor authentication (2FA) is required. Provide an OTP code to complete the login.")


class AgreementNotAcceptedError(Error):
    """Raised when one or more terms/policies have been updated and need acceptance."""

    def __init__(self, pending_types: list[int] | None = None):
        self.pending_types = pending_types or []
        type_names = {1: "Terms & Conditions", 2: "Privacy Policy", 3: "Service Agreement"}
        names = [type_names.get(t, f"Type {t}") for t in self.pending_types]
        super().__init__(f"The following agreements need acceptance: {', '.join(names)}")