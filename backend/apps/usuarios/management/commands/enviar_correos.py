from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.usuarios.models import CorreoPendiente, LimiteAcceso


class Command(BaseCommand):
    help = "Procesa correos pendientes con reserva de trabajo y reintentos; programar cada minuto."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limite", type=int, default=50)

    def handle(self, *args, **options) -> None:
        enviados = 0
        for _ in range(options["limite"]):
            with transaction.atomic():
                correo = CorreoPendiente.objects.select_for_update(skip_locked=True).filter(
                    enviado_en__isnull=True, proximo_intento__lte=timezone.now(), intentos__lt=5
                ).order_by("id").first()
                if correo is None:
                    break
                correo.intentos += 1
                correo.proximo_intento = timezone.now() + timedelta(minutes=5 * correo.intentos)
                correo.save(update_fields=["intentos", "proximo_intento"])
            try:
                send_mail(correo.asunto, correo.contenido, settings.DEFAULT_FROM_EMAIL,
                          [correo.destinatario], fail_silently=False)
            except OSError:
                # No registrar excepciones SMTP: pueden contener destinatarios/credenciales.
                self.stderr.write(f"Correo {correo.pk}: envío pendiente de reintento.")
            else:
                correo.enviado_en = timezone.now()
                correo.contenido = ""  # No conservar enlaces sensibles tras la entrega.
                correo.save(update_fields=["enviado_en", "contenido"])
                enviados += 1
        LimiteAcceso.objects.filter(vence_en__lt=timezone.now()).delete()
        self.stdout.write(f"Correos enviados: {enviados}")
