from django.db import models
from django.utils import timezone


class LimiteAcceso(models.Model):
    clave = models.CharField(max_length=64, unique=True)
    intentos = models.PositiveIntegerField(default=0)
    vence_en = models.DateTimeField()

    class Meta:
        db_table = "usuarios_limites_acceso"


class CorreoPendiente(models.Model):
    destinatario = models.EmailField()
    asunto = models.CharField(max_length=180)
    contenido = models.TextField()
    intentos = models.PositiveIntegerField(default=0)
    proximo_intento = models.DateTimeField(default=timezone.now, db_index=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios_correos_pendientes"
