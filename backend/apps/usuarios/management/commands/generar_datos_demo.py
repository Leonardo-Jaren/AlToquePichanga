"""Provisiona un conjunto local de cuentas, horarios y tarifas para pruebas."""

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
_GUIA_LOCAL = """
## Comprobaciones manuales de Fase 4B

Inicia sesión normalmente en `/ingresar`; las contraseñas de prueba se conservan en este
archivo local. Después abre las rutas indicadas en `docs/USUARIOS_PRUEBA.md`:

- Dueño: `/panel/dueno` → **Calendario**. Para probar otra sede, elige una cancha de A Norte.
- Administrador de sede: `/panel/administrador_sede` → sede A Centro → **Calendario**.
- Cajero: `/panel/cajero` → **Calendario**; solo puede consultar.
- Superadministrador: `/panel/plataforma` → **Calendario**; consulta el alcance global.
- Jugadores A y B: inicia sesión en ventanas/perfiles de navegador independientes y abre
  `/canchas-publicas` con la misma cancha y fecha. A retiene 19:00\u201320:00; B debe verla ocupada
  sin recargar. Cancela desde `/mis-reservas` en A y confirma que B vuelve a verla libre.
- Para ver la matriz de empresa: dueño A → `/panel/dueno` → **Calendario**. El jugador no puede
  consultar una cancha privada; el administrador de sede sí, solo en sedes asignadas.

En `/canchas-publicas`, selecciona el próximo lunes y la cancha `[DEMO ALTOQUE] Cancha A
heredada`: 18:00 a 19:00 queda retenida, 19:00 a 20:00 queda libre y 21:00 a 22:00 tiene una
retención vencida que ya liberó el horario. En `[DEMO ALTOQUE] Cancha B Centro 1`, 19:00 a 21:00
es una retención de dos horas en la empresa B. Estas retenciones duran el valor provisional
configurado (15 minutos) desde la primera ejecución; repite el comando para restaurar solo
los datos maestros, pero no se reabren retenciones vencidas o canceladas. Las solicitudes superpuestas se comprueban
con las pruebas de concurrencia; nunca se siembran dos reservas activas que choquen.

## Comprobaciones manuales de Fase 4C

- Jugador: abre `/mis-reservas`, entra a **Pago** en una reserva demo y revisa adelanto,
  total, saldo, medio, historial y estados. Si venció el plazo provisional, crea una nueva
  retención desde `/canchas-publicas` para recorrer el flujo completo.
- Dueño A o administrador A: `/panel/dueno` o `/panel/administrador_sede` → **Pagos**;
  revisa la cola y configura cuentas ficticias. Cajero A → **Pagos** para revisar sin editar
  las cuentas. Dueño B solo consulta los pagos de su empresa.
- El comando crea titulares, cuentas y WhatsApp con ceros, identificados como demo. Son
  datos inválidos de prueba: no abras el enlace de WhatsApp ni realices un pago real.
- El botón de WhatsApp solo prepara el mensaje. La captura se adjunta manualmente y el
  estado no cambia a aprobado hasta que un empleado lo revise.
"""
_GUIA_LOCAL_ANTERIOR_FASE3D = """
## Comprobaciones manuales de Fase 3D

Inicia sesión normalmente en `/ingresar`; las contraseñas de prueba se conservan en este
archivo local. Después abre las rutas indicadas en `docs/USUARIOS_PRUEBA.md`:

- Dueño: `/panel/dueno` → **Calendario**. Para probar otra sede, elige una cancha de A Norte.
- Administrador de sede: `/panel/administrador_sede` → sede A Centro → **Calendario**.
- Cajero: `/panel/cajero` → **Calendario**; solo puede consultar.
- Superadministrador: `/panel/plataforma` → **Calendario**; consulta el alcance global.
- Jugador: `/canchas-publicas`. La consulta no necesita sesión; si inicias con el usuario
  jugador, la vista sigue mostrando únicamente canchas publicadas.

En el calendario, prueba los controles **Día** y **Semana**, el detalle de los bloques y una
cotización de varias horas. Para comprobar aislamiento, alterna entre dueño A y dueño B. La
cancha `[DEMO ALTOQUE] Cancha A heredada` y `[DEMO ALTOQUE] Cancha B Centro 1` quedan
publicadas localmente por el seeder. La selección no crea reservas ni bloquea horarios.
"""
_ROLES = tuple(CORREOS)
_ROLES_ANTERIORES = tuple(rol for rol in _ROLES if rol != "jugador_b")
_GUIA_LOCAL_ANTERIOR_FASE4A = """
## Comprobaciones manuales de Fase 4A

Inicia sesión normalmente en `/ingresar`; las contraseñas de prueba se conservan en este
archivo local. Después abre las rutas indicadas en `docs/USUARIOS_PRUEBA.md`:

- Dueño: `/panel/dueno` → **Calendario**. Para probar otra sede, elige una cancha de A Norte.
- Administrador de sede: `/panel/administrador_sede` → sede A Centro → **Calendario**.
- Cajero: `/panel/cajero` → **Calendario**; solo puede consultar.
- Superadministrador: `/panel/plataforma` → **Calendario**; consulta el alcance global.
- Jugador: `/canchas-publicas` y `/mis-reservas`. Inicia sesión como jugador para solicitar,
  consultar o cancelar retenciones propias.

En `/canchas-publicas`, selecciona el próximo lunes y la cancha `[DEMO ALTOQUE] Cancha A
heredada`: 18:00 a 19:00 queda retenida, 19:00 a 20:00 queda libre y 21:00 a 22:00 tiene una
retención vencida que ya liberó el horario. En `[DEMO ALTOQUE] Cancha B Centro 1`, 19:00 a 21:00
es una retención de dos horas en la empresa B. Estas retenciones duran el valor provisional
configurado (15 minutos) desde la primera ejecución; repite el comando para restaurar solo
los datos maestros, pero no se reabren retenciones vencidas o canceladas. Las solicitudes superpuestas se comprueban
con las pruebas de concurrencia; nunca se siembran dos reservas activas que choquen.
"""
_GUIA_LOCAL_ANTERIOR_FASE4B = """
## Comprobaciones manuales de Fase 4B

Inicia sesión normalmente en `/ingresar`; las contraseñas de prueba se conservan en este
archivo local. Después abre las rutas indicadas en `docs/USUARIOS_PRUEBA.md`:

- Dueño: `/panel/dueno` → **Calendario**. Para probar otra sede, elige una cancha de A Norte.
- Administrador de sede: `/panel/administrador_sede` → sede A Centro → **Calendario**.
- Cajero: `/panel/cajero` → **Calendario**; solo puede consultar.
- Superadministrador: `/panel/plataforma` → **Calendario**; consulta el alcance global.
- Jugadores A y B: inicia sesión en ventanas/perfiles de navegador independientes y abre
  `/canchas-publicas` con la misma cancha y fecha. A retiene 19:00\u201320:00; B debe verla ocupada
  sin recargar. Cancela desde `/mis-reservas` en A y confirma que B vuelve a verla libre.
- Para ver la matriz de empresa: dueño A → `/panel/dueno` → **Calendario**. El jugador no puede
  consultar una cancha privada; el administrador de sede sí, solo en sedes asignadas.

En `/canchas-publicas`, selecciona el próximo lunes y la cancha `[DEMO ALTOQUE] Cancha A
heredada`: 18:00 a 19:00 queda retenida, 19:00 a 20:00 queda libre y 21:00 a 22:00 tiene una
retención vencida que ya liberó el horario. En `[DEMO ALTOQUE] Cancha B Centro 1`, 19:00 a 21:00
es una retención de dos horas en la empresa B. Estas retenciones duran el valor provisional
configurado (15 minutos) desde la primera ejecución; repite el comando para restaurar solo
los datos maestros, pero no se reabren retenciones vencidas o canceladas. Las solicitudes superpuestas se comprueban
con las pruebas de concurrencia; nunca se siembran dos reservas activas que choquen.
"""


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


def _renderizar_bloque_credenciales(credenciales: dict) -> str:
    contenido = json.dumps(credenciales, ensure_ascii=False, indent=2, sort_keys=False)
    return f"{_ENCABEZADO}```json\n{contenido}\n```\n"


def _renderizar(credenciales: dict) -> str:
    return _renderizar_bloque_credenciales(credenciales) + _GUIA_LOCAL


def _validar_estructura(credenciales: object) -> dict:
    if not isinstance(credenciales, dict) or set(credenciales) != {"version", "usuarios"}:
        raise CommandError("El archivo local de credenciales no tiene el formato del seeder.")
    if credenciales["version"] != 1 or not isinstance(credenciales["usuarios"], dict):
        raise CommandError("El archivo local de credenciales no tiene una versión compatible.")
    roles = set(credenciales["usuarios"])
    if roles not in (set(_ROLES), set(_ROLES_ANTERIORES)):
        raise CommandError("El archivo local de credenciales contiene cuentas inesperadas.")
    for rol in roles:
        entrada = credenciales["usuarios"][rol]
        if not isinstance(entrada, dict) or set(entrada) != {"correo", "contrasena"}:
            raise CommandError("El archivo local de credenciales contiene campos ajenos.")
        if entrada["correo"] != CORREOS[rol]:
            raise CommandError("El archivo local de credenciales contiene un correo inesperado.")
        password = entrada["contrasena"]
        if not isinstance(password, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,}", password):
            raise CommandError("El archivo local de credenciales contiene una contraseña inválida.")
    if roles == set(_ROLES_ANTERIORES):
        credenciales = {
            **credenciales,
            "usuarios": {
                **credenciales["usuarios"],
                "jugador_b": {
                    "correo": CORREOS["jugador_b"],
                    "contrasena": secrets.token_urlsafe(48),
                },
            },
        }
    return credenciales


def _leer_o_generar_credenciales(ruta: Path) -> tuple[dict, str, str | None]:
    if ruta.is_symlink():
        raise CommandError("El archivo local de credenciales no puede ser un enlace simbólico.")
    if ruta.exists():
        try:
            contenido = ruta.read_text(encoding="utf-8")
            if not contenido.startswith(_ENCABEZADO):
                raise CommandError(
                    "USUARIOS_PRUEBA_LOCAL.md ya existe y no pertenece al seeder; no se sobrescribió."
                )
            inicio = len(_ENCABEZADO)
            apertura = "```json\n"
            cierre = "\n```\n"
            if not contenido.startswith(apertura, inicio):
                raise CommandError("El archivo local de credenciales tiene contenido ajeno.")
            inicio_json = inicio + len(apertura)
            fin_json = contenido.find(cierre, inicio_json)
            if fin_json < 0:
                raise CommandError("El archivo local de credenciales tiene contenido ajeno.")
            datos_archivo = json.loads(contenido[inicio_json:fin_json])
            bloque_anterior = _renderizar_bloque_credenciales(datos_archivo)
            datos = _validar_estructura(datos_archivo)
            bloque_actual = _renderizar_bloque_credenciales(datos)
            permitidos = {
                bloque_anterior,
                bloque_anterior + _GUIA_LOCAL_ANTERIOR_FASE3D,
                bloque_anterior + _GUIA_LOCAL_ANTERIOR_FASE4A,
                bloque_anterior + _GUIA_LOCAL_ANTERIOR_FASE4B,
                bloque_actual,
                _renderizar(datos),
            }
            if contenido not in permitidos:
                raise CommandError("El archivo local de credenciales tiene contenido ajeno.")
            estado = "conservar" if contenido == _renderizar(datos) else "actualizar"
            return datos, estado, contenido
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError("No se pudo leer el archivo local de credenciales.") from exc

    datos = {
        "version": 1,
        "usuarios": {
            rol: {"correo": CORREOS[rol], "contrasena": secrets.token_urlsafe(48)}
            for rol in _ROLES
        },
    }
    return datos, "crear", None


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


def _actualizar_guia_local(ruta: Path, contenido_anterior: str, credenciales: dict) -> None:
    """Actualiza únicamente un archivo del seeder cuya estructura se validó."""
    try:
        if ruta.is_symlink() or ruta.read_text(encoding="utf-8") != contenido_anterior:
            raise CommandError("El archivo local cambió durante la ejecución; no se sobrescribió.")
    except OSError as exc:
        raise CommandError("No se pudo volver a validar el archivo local de credenciales.") from exc

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
        os.replace(temporal, ruta)
    except OSError as exc:
        raise CommandError("No se pudo actualizar la guía local de credenciales.") from exc
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
        credenciales, estado_archivo, contenido_anterior = _leer_o_generar_credenciales(ruta)
        with transaction.atomic():
            bloquear_ejecucion_concurrente()
            crear_datos_demo(credenciales)
            if estado_archivo == "crear":
                _guardar_credenciales_nuevas(ruta, credenciales)
            elif estado_archivo == "actualizar":
                _actualizar_guia_local(ruta, contenido_anterior or "", credenciales)
        self.stdout.write(self.style.SUCCESS(
            "Datos demo locales listos: 7 cuentas, 2 empresas, 4 sedes, 6 canchas, 22 tarifas "
            "3 reservas, 12 medios de pago y 5 pagos ficticios. Las contraseñas están solo "
            "en docs/USUARIOS_PRUEBA_LOCAL.md."
        ))
