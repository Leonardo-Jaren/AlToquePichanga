from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    correo = models.EmailField(null=True, blank=True)
    correo_verificado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios_perfiles"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(Lower("correo"), name="perfil_correo_unico")
        ]


class IdentidadGoogle(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identidad_google"
    )
    identificador = models.CharField(max_length=255, unique=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios_identidades_google"
