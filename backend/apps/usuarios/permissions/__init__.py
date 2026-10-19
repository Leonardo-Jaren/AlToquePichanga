from rest_framework.authentication import SessionAuthentication


class SesionConCSRF(SessionAuthentication):
    """DRF normalmente omite CSRF en usuarios anónimos: también proteger login/registro."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)

    def authenticate_header(self, request) -> str:
        return "Session"
