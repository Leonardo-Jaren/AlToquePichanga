class RespuestaPrivadaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        privada = request.path.startswith(("/api/auth/", "/api/empresas/", "/api/panel/"))
        if privada:
            request.sensitive_post_parameters = "__ALL__"
        respuesta = self.get_response(request)
        if privada:
            respuesta["Cache-Control"] = "no-store"
            respuesta["Referrer-Policy"] = "no-referrer"
        return respuesta
