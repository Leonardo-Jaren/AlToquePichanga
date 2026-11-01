from typing import ClassVar

from django.db import models


class NotificacionReserva(models.Model):
    reserva = models.ForeignKey("reservas.Reserva", on_delete=models.PROTECT, related_name="notificaciones")
    tipo = models.CharField(max_length=24)
    correo = models.OneToOneField("usuarios.CorreoPendiente", on_delete=models.PROTECT, related_name="notificacion_reserva")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas_notificaciones"
        constraints: ClassVar[list] = [models.UniqueConstraint(fields=["reserva", "tipo"], name="reserva_notificacion_tipo_unico")]
