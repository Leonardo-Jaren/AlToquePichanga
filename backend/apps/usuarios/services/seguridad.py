from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import Throttled

from apps.usuarios.models import LimiteAcceso


def limitar(ambito: str, identificador: str, maximo: int) -> None:
    """Contadores compartidos en PostgreSQL; nunca confiar en X-Forwarded-For del cliente."""
    clave = salted_hmac("limite_acceso", f"{ambito}:{identificador}", algorithm="sha256").hexdigest()
    ahora = timezone.now()
    with transaction.atomic():
        limite, _ = LimiteAcceso.objects.get_or_create(
            clave=clave,
            defaults={"vence_en": ahora + timedelta(seconds=settings.AUTH_RATE_WINDOW)},
        )
        limite = LimiteAcceso.objects.select_for_update().get(pk=limite.pk)
        if limite.vence_en <= ahora:
            limite.intentos = 0
            limite.vence_en = ahora + timedelta(seconds=settings.AUTH_RATE_WINDOW)
        if limite.intentos >= maximo:
            raise Throttled(
                wait=max(1, int((limite.vence_en - ahora).total_seconds())),
                detail="Demasiados intentos. Intenta nuevamente en unos minutos.",
            )
        limite.intentos += 1
        limite.save(update_fields=["intentos", "vence_en"])
