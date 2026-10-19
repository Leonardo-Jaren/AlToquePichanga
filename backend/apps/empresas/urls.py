from django.urls import path

from apps.empresas.views import EmpresaView
from apps.empresas.views.administracion import (
    EmpresaAdministradaView,
    EmpresaPlataformaView,
    EmpresasAdministradasView,
    EmpresasPlataformaView,
    EmpresasView,
)
from apps.empresas.views.personal import (
    AceptarInvitacionView,
    PersonalEmpresaView,
    RevocarInvitacionView,
    RevocarPersonalView,
)
from apps.suscripciones.views import SuscripcionEmpresaView

urlpatterns = [
    path("", EmpresasView.as_view(), name="empresas"),
    path("administradas/", EmpresasAdministradasView.as_view(), name="empresas-administradas"),
    path("administradas/<int:identificador>/", EmpresaAdministradaView.as_view()),
    path("administradas/<int:empresa_id>/personal/", PersonalEmpresaView.as_view()),
    path("administradas/<int:empresa_id>/personal/<int:membresia_id>/revocar/", RevocarPersonalView.as_view()),
    path("administradas/<int:empresa_id>/invitaciones/<int:invitacion_id>/revocar/", RevocarInvitacionView.as_view()),
    path("administradas/<int:empresa_id>/suscripcion/", SuscripcionEmpresaView.as_view()),
    path("plataforma/", EmpresasPlataformaView.as_view()),
    path("plataforma/<int:identificador>/", EmpresaPlataformaView.as_view()),
    path("<int:identificador>/", EmpresaView.as_view()),
    path("invitaciones/aceptar/", AceptarInvitacionView.as_view()),
]
