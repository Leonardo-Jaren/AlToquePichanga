from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.services.acceso import (
    acceso_panel,
    acceso_panel_limitado,
    consultar_empresa,
    consultar_empresas,
)


class EmpresasView(APIView):
    def get(self, request):
        return Response(consultar_empresas(request.user))


class EmpresaView(APIView):
    def get(self, request, identificador: int):
        return Response(consultar_empresa(request.user, identificador))


class PanelView(APIView):
    def get(self, request, rol: str):
        try:
            return Response(acceso_panel(request.user, rol))
        except PermissionDenied:
            limitado = acceso_panel_limitado(request.user, rol)
            if limitado:
                return Response(limitado)
            raise
