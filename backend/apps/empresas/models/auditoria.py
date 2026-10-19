from typing import ClassVar

from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    empresa = models.ForeignKey(
        "empresas.Empresa", null=True, blank=True, on_delete=models.PROTECT
    )
    accion = models.CharField(max_length=80)
    recurso = models.CharField(max_length=60)
    recurso_id = models.PositiveBigIntegerField(null=True, blank=True)
    datos = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "empresas_registros_auditoria"
        ordering: ClassVar[list[str]] = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return f"{self.accion} {self.recurso}"

