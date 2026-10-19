"""Provisiona un conjunto local de cuentas para revisar los roles y horarios."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.usuarios.services.datos_demo import (
    CORREOS,
    bloquear_ejecucion_concurrente,
    crear_datos_demo,
)

_ENCABEZADO = (
    "# Credenciales locales de AlToque Pichanga (no compartir)\n\n"
    "<!-- ALTOQUE_DEMO_CREDENTIALS_V1 -->\n"
)
_ROLES = tuple(CORREOS)


def _ruta_credenciales() -> Path:
    """Devuelve el archivo local ignorado en la raíz del proyecto."""
    return Path(settings.BASE_DIR).parent / "docs" / "USUARIOS_PRUEBA_LOCAL.md"


def _validar_entorno() -> None:
    if settings.DEBUG is not True:
        raise CommandError("El seeder demo solo se permite con DEBUG=True.")
    if os.environ.get("ALTOQUE_PERMITIR_DATOS_DEMO") != "1":
        raise CommandError("Define ALTOQUE_PERMITIR_DATOS_DEMO=1 para confirmar el seeder local.")
    base = settings.DATABASES.get("default", {})
    if base.get("ENGINE") != "django.db.backends.postgresql":
        raise CommandError("El seeder demo requiere PostgreSQL local.")
    host = str(base.get("HOST", "")).strip().casefold()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise CommandError("El seeder demo solo permite una base PostgreSQL de loopback.")


def _renderizar(credenciales: dict) -> str:
    contenido = json.dumps(credenciales, ensure_ascii=False, indent=2, sort_keys=False)
    return f"{_ENCABEZADO}```json\n{contenido}\n```\n"


def _validar_estructura(credenciales: object) -> dict:
    if not isinstance(credenciales, dict) or set(credenciales) != {"version", "usuarios"}:
        raise CommandError("El archivo local de credenciales no tiene el formato del seeder.")
    if credenciales["version"] != 1 or not isinstance(credenciales["usuarios"], dict):
        raise CommandError("El archivo local de credenciales no tiene una versión compatible.")
    if set(credenciales["usuarios"]) != set(_ROLES):
        raise CommandError("El archivo local de credenciales contiene cuentas inesperadas.")
    for rol in _ROLES:
        entrada = credenciales["usuarios"][rol]
        if not isinstance(entrada, dict) or set(entrada) != {"correo", "contrasena"}:
            raise CommandError("El archivo local de credenciales contiene campos ajenos.")
        if entrada["correo"] != CORREOS[rol]:
            raise CommandError("El archivo local de credenciales contiene un correo inesperado.")
        password = entrada["contrasena"]
        if not isinstance(password, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,}", password):
            raise CommandError("El archivo local de credenciales contiene una contraseña inválida.")
    return credenciales


def _leer_o_generar_credenciales(ruta: Path) -> tuple[dict, bool]:
    if ruta.is_symlink():
        raise CommandError("El archivo local de credenciales no puede ser un enlace simbólico.")
    if ruta.exists():
        try:
            contenido = ruta.read_text(encoding="utf-8")
            if not contenido.startswith(_ENCABEZADO) or not contenido.endswith("\n```\n"):
                raise CommandError(
                    "USUARIOS_PRUEBA_LOCAL.md ya existe y no pertenece al seeder; no se sobrescribió."
                )
            bloque = contenido[len(_ENCABEZADO):-5]
            if not bloque.startswith("```json\n"):
                raise CommandError("El archivo local de credenciales tiene contenido ajeno.")
            datos = _validar_estructura(json.loads(bloque[8:]))
            if _renderizar(datos) != contenido:
                raise CommandError("El archivo local de credenciales tiene contenido ajeno.")
            return datos, False
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError("No se pudo leer el archivo local de credenciales.") from exc

    datos = {
        "version": 1,
        "usuarios": {
            rol: {"correo": CORREOS[rol], "contrasena": secrets.token_urlsafe(48)}
            for rol in _ROLES
        },
    }
    return datos, True


def _guardar_credenciales_nuevas(ruta: Path, credenciales: dict) -> None:
    if not ruta.parent.is_dir():
        raise CommandError("No existe docs/; crea esa carpeta antes de ejecutar el seeder.")
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=ruta.parent,
            prefix=".usuarios-prueba-", suffix=".tmp", delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(_renderizar(credenciales))
        try:
            os.chmod(temporal, 0o600)
        except OSError:
            pass
        # Un enlace duro crea el destino de forma exclusiva; nunca pisa contenido ajeno.
        os.link(temporal, ruta)
    except FileExistsError as exc:
        raise CommandError("El archivo local de credenciales apareció durante la ejecución.") from exc
    except OSError as exc:
        raise CommandError("No se pudo crear el archivo local de credenciales.") from exc
    finally:
        if temporal is not None:
            try:
                temporal.unlink(missing_ok=True)
            except OSError:
                pass


class Command(BaseCommand):
    help = "Crea usuarios y datos demo únicamente en PostgreSQL local con opt-in explícito."

    def handle(self, *args, **options) -> None:
        _validar_entorno()
        ruta = _ruta_credenciales()
        credenciales, generar_archivo = _leer_o_generar_credenciales(ruta)
        with transaction.atomic():
            bloquear_ejecucion_concurrente()
            crear_datos_demo(credenciales)
            if generar_archivo:
                _guardar_credenciales_nuevas(ruta, credenciales)
        self.stdout.write(self.style.SUCCESS(
            "Datos demo locales listos: 6 cuentas, 2 empresas, 4 sedes y 6 canchas. "
            "Las contraseñas están solo en docs/USUARIOS_PRUEBA_LOCAL.md."
        ))
