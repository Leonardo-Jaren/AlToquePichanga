from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.empresas.models.empresa import RolEmpresa


class InvitacionEmpleado(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.PROTECT, related_name="invitaciones"
    )
    correo = models.EmailField()
    rol = models.CharField(max_length=24, choices=RolEmpresa.choices)
    sedes = models.ManyToManyField("sedes.Sede", related_name="invitaciones", blank=True)
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invitaciones_creadas"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    vence_en = models.DateTimeField()
    aceptada_en = models.DateTimeField(null=True, blank=True)
    cancelada_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "empresas_invitaciones_empleado"
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(rol__in=RolEmpresa.values),
                name="invitacion_rol_autorizado",
            ),
            models.UniqueConstraint(
                Lower("correo"), "empresa",
                condition=Q(aceptada_en__isnull=True, cancelada_en__isnull=True),
                name="invitacion_pendiente_unica",
            ),
        ]
