from django.urls import path

from apps.suscripciones.views import PlanesView

urlpatterns = [path("planes/", PlanesView.as_view())]
