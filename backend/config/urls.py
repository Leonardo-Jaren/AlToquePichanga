"""
URL Configuration for AlToque Pichanga.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.empresas.views import PanelView
from shared.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health_check"),
    path("api/auth/", include("apps.usuarios.urls")),
    path("api/empresas/", include("apps.empresas.urls")),
    path("api/sedes/", include("apps.sedes.urls")),
    path("api/canchas/", include("apps.canchas.urls")),
    path("api/horarios/", include("apps.horarios.urls")),
    path("api/suscripciones/", include("apps.suscripciones.urls")),
    path("api/plataforma/", include("apps.suscripciones.urls_plataforma")),
    path("api/panel/<str:rol>/", PanelView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
