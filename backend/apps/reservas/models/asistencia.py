from django.conf import settings
from django.db import models


class AsistenciaReserva(models.Model):
    reserva = models.OneToOneField("reservas.Reserva", on_delete=models.PROTECT, related_name="asistencia")
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asistencias_registradas")
    registrada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas_asistencias"
