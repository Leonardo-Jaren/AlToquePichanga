import time

from django.core.management.base import BaseCommand, CommandError

from apps.reservas.services.retenciones import vencer_retenciones_vencidas


class Command(BaseCommand):
    help = "Vence las retenciones temporales expiradas y libera sus horarios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--continuo", action="store_true",
            help="Revisa retenciones vencidas continuamente para desarrollo o supervisor.",
        )
        parser.add_argument(
            "--intervalo", type=int, default=60,
            help="Segundos entre revisiones cuando se usa --continuo (mínimo: 1).",
        )

    def handle(self, *args, **options):
        intervalo = options["intervalo"]
        if intervalo < 1:
            raise CommandError("--intervalo debe ser un entero positivo.")
        continuo = options["continuo"]
        while True:
            cantidad = vencer_retenciones_vencidas()
            self.stdout.write(self.style.SUCCESS(
                f"Retenciones vencidas y liberadas: {cantidad}."
            ))
            if not continuo:
                return
            try:
                time.sleep(intervalo)
            except KeyboardInterrupt:
                self.stdout.write("Proceso de vencimientos detenido.")
                return
