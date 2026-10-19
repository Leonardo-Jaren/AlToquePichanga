from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = "Crea perfiles de usuarios provisionados con createsuperuser, sin asignar roles."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        correos = set(PerfilUsuario.objects.exclude(correo=None).values_list("correo", flat=True))
        usuarios = list(User.objects.filter(perfil__isnull=True))
        normalizados = [u.email.strip().lower() for u in usuarios if u.email.strip()]
        if len(set(normalizados)) != len(normalizados) or correos.intersection(normalizados):
            raise CommandError("Resuelve los correos duplicados antes de sincronizar perfiles.")
        for usuario in usuarios:
            PerfilUsuario.objects.create(usuario=usuario, correo=usuario.email.strip().lower() or None)
        self.stdout.write(f"Perfiles creados: {len(usuarios)}")
