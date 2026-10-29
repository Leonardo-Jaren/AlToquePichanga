"""WebSocket de avisos de disponibilidad con alcance validado en servidor."""

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.utils import timezone

from apps.canchas.repositories.canchas import canchas_visibles
from apps.canchas.services.publicacion import canchas_publicadas
from apps.empresas.models import AccesoPlataforma
from apps.reservas.services.eventos import grupo_disponibilidad

MAX_CANCHAS = 24
MAX_DIAS = 7


class DisponibilidadConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        try:
            self.cancha_ids, self.fechas = self._leer_suscripcion()
        except (KeyError, TypeError, UnicodeDecodeError, ValueError):
            await self.close(code=4400)
            return

        user = self.scope.get("user", AnonymousUser())
        autorizado, acceso_global = await _validar_alcance(user, self.cancha_ids)
        if not autorizado:
            await self.close(code=4403)
            return
        if acceso_global:
            await _auditar_acceso_global(user.pk)

        self.grupos = [
            grupo_disponibilidad(cancha_id)
            for cancha_id in self.cancha_ids
        ] + [
            grupo_disponibilidad(cancha_id, fecha)
            for cancha_id in self.cancha_ids
            for fecha in self.fechas
        ]
        for grupo in self.grupos:
            await self.channel_layer.group_add(grupo, self.channel_name)
        await self.accept()

    def _leer_suscripcion(self) -> tuple[list[int], list[date]]:
        query = parse_qs(self.scope.get("query_string", b"").decode("ascii"), strict_parsing=True)
        valores = query.get("canchas", [])
        if len(valores) != 1:
            raise ValueError("Se requiere una lista de canchas.")
        ids = [int(valor) for valor in valores[0].split(",")]
        if not ids or len(ids) > MAX_CANCHAS or any(valor < 1 for valor in ids):
            raise ValueError("Límite de canchas inválido.")
        if len(set(ids)) != len(ids):
            raise ValueError("No se permiten canchas duplicadas.")
        desde = date.fromisoformat(query["desde"][0])
        hasta = date.fromisoformat(query["hasta"][0])
        if (hasta < desde or (hasta - desde).days >= MAX_DIAS):
            raise ValueError("El rango debe abarcar entre uno y siete días.")
        return ids, [desde + timedelta(days=dias) for dias in range((hasta - desde).days + 1)]

    async def receive(self, text_data=None, bytes_data=None) -> None:
        # La conexión es de solo difusión; ningún mensaje del cliente muta datos.
        longitud = len(text_data or bytes_data or b"")
        await self.close(code=4400 if longitud <= 1024 else 4409)

    async def disponibilidad_actualizada(self, mensaje: dict) -> None:
        if not await _sesion_y_alcance_vigentes(
            self.scope.get("user", AnonymousUser()),
            self.cancha_ids,
            getattr(self.scope.get("session"), "session_key", None),
        ):
            await self.close(code=4401)
            return
        evento = mensaje.get("evento", {})
        if evento.get("tipo") != "disponibilidad_actualizada":
            return
        try:
            cancha_id = int(evento["cancha_id"])
            fecha = date.fromisoformat(evento["fecha"]) if evento.get("fecha") else None
        except (KeyError, TypeError, ValueError):
            return
        if cancha_id not in self.cancha_ids or (fecha is not None and fecha not in self.fechas):
            return
        await self.send_json({
            "tipo": "disponibilidad_actualizada",
            "cancha_id": cancha_id,
            "fecha": fecha.isoformat() if fecha else None,
            "motivo": evento.get("motivo"),
        })

    async def disconnect(self, code) -> None:
        for grupo in getattr(self, "grupos", []):
            await self.channel_layer.group_discard(grupo, self.channel_name)


@database_sync_to_async
def _validar_alcance(usuario, ids: list[int]) -> tuple[bool, bool]:
    if getattr(usuario, "is_authenticated", False) and not usuario.is_active:
        return False, False
    publicadas = set(canchas_publicadas().filter(pk__in=ids).values_list("pk", flat=True))
    privadas: set[int] = set()
    if getattr(usuario, "is_authenticated", False):
        privadas = set(canchas_visibles(usuario).filter(pk__in=ids).values_list("pk", flat=True))
    autorizado = all(cancha_id in publicadas or cancha_id in privadas for cancha_id in ids)
    acceso_global = bool(getattr(usuario, "is_superuser", False) and ids and any(
        cancha_id not in publicadas for cancha_id in ids
    ))
    return autorizado, acceso_global


@database_sync_to_async
def _auditar_acceso_global(usuario_id: int) -> None:
    AccesoPlataforma.objects.create(
        usuario_id=usuario_id, accion="suscribir_disponibilidad_global"
    )


@database_sync_to_async
def _sesion_y_alcance_vigentes(usuario, ids: list[int], session_key: str | None) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        publicadas = set(canchas_publicadas().filter(pk__in=ids).values_list("pk", flat=True))
        return all(cancha_id in publicadas for cancha_id in ids)
    usuario_actual = get_user_model().objects.filter(
        pk=getattr(usuario, "pk", None), is_active=True
    ).first()
    if usuario_actual is None or not session_key:
        return False
    session = Session.objects.filter(
        session_key=session_key, expire_date__gt=timezone.now()
    ).first()
    if session is None:
        return False
    datos = session.get_decoded()
    if str(datos.get("_auth_user_id")) != str(usuario_actual.pk):
        return False
    publicadas = set(canchas_publicadas().filter(pk__in=ids).values_list("pk", flat=True))
    privadas = set(canchas_visibles(usuario_actual).filter(pk__in=ids).values_list("pk", flat=True))
    return all(cancha_id in publicadas or cancha_id in privadas for cancha_id in ids)
