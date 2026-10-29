import asyncio
import os
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from channels.db import database_sync_to_async
from channels.layers import channel_layers, get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from django.test import override_settings
from django.utils import timezone

from apps.canchas.models import Cancha
from apps.reservas.consumers.disponibilidad import DisponibilidadConsumer
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.eventos import programar_cambio_disponibilidad
from apps.reservas.services.reservas import cancelar_retencion, crear_retencion
from apps.reservas.services.retenciones import vencer_retenciones_vencidas
from config.asgi import application
from tests.test_fase4a_reservas import _contexto

pytestmark = pytest.mark.django_db(transaction=True)
ORIGEN = [(b"origin", b"http://localhost:5173")]


def _url(*ids, desde, hasta):
    ids_texto = ",".join(str(valor) for valor in ids)
    return f"/ws/disponibilidad/?canchas={ids_texto}&desde={desde}&hasta={hasta}"


def ejecutar_async(caso):
    def wrapper(*args, **kwargs):
        return asyncio.run(caso(*args, **kwargs))

    return wrapper


async def _sync(funcion, *args, **kwargs):
    return await database_sync_to_async(funcion, thread_sensitive=True)(*args, **kwargs)


def _comunicador(url, usuario=None, session=None):
    comunicador = WebsocketCommunicator(
        DisponibilidadConsumer.as_asgi(), url, headers=ORIGEN
    )
    comunicador.scope["user"] = usuario or AnonymousUser()
    comunicador.scope["session"] = session
    return comunicador


def _sesion(usuario):
    almacen = SessionStore()
    almacen["_auth_user_id"] = str(usuario.pk)
    almacen["_auth_user_backend"] = f"{ModelBackend.__module__}.{ModelBackend.__qualname__}"
    almacen["_auth_user_hash"] = usuario.get_session_auth_hash()
    almacen.save()
    return almacen


async def _crear(usuario, cancha, dia, hora="19:00"):
    return await _sync(
        crear_retencion, usuario, cancha.pk, dia,
        datetime.strptime(hora, "%H:%M").time(), 1, uuid4(),
    )


@ejecutar_async
async def test_dos_sesiones_publicas_reciben_creacion_cancelacion_y_vencimiento():
    _, _, _, cancha, dia = await _sync(_contexto, "ws-owner-a@example.test")
    jugador = await _sync(
        User.objects.create_user, "ws-player@example.test", "ws-player@example.test"
    )
    url = _url(cancha.pk, desde=dia.isoformat(), hasta=dia.isoformat())
    primero, segundo = _comunicador(url), _comunicador(url)
    assert (await primero.connect())[0] is True
    assert (await segundo.connect())[0] is True
    try:
        reserva, creada = await _crear(jugador, cancha, dia)
        assert creada
        mensaje_a = await primero.receive_json_from(timeout=2)
        mensaje_b = await segundo.receive_json_from(timeout=2)
        esperado = {
            "tipo": "disponibilidad_actualizada", "cancha_id": cancha.pk,
            "fecha": dia.isoformat(), "motivo": "retencion_creada",
        }
        assert mensaje_a == mensaje_b == esperado
        assert not set(mensaje_a) & {"jugador", "correo", "importe", "reserva", "empresa"}

        await _sync(cancelar_retencion, jugador, reserva.codigo)
        assert (await primero.receive_json_from(timeout=2))["motivo"] == "retencion_cancelada"
        assert (await segundo.receive_json_from(timeout=2))["motivo"] == "retencion_cancelada"

        vencida, _ = await _crear(jugador, cancha, dia, "20:00")
        await primero.receive_json_from(timeout=2)
        await segundo.receive_json_from(timeout=2)
        await _sync(
            Reserva.objects.filter(pk=vencida.pk).update,
            retencion_vence_en=timezone.now() - timedelta(seconds=1),
        )
        assert await _sync(vencer_retenciones_vencidas) == 1
        assert (await primero.receive_json_from(timeout=2))["motivo"] == "retencion_vencida"
        assert (await segundo.receive_json_from(timeout=2))["motivo"] == "retencion_vencida"
        await _sync(vencida.refresh_from_db)
        assert vencida.estado == EstadoReserva.VENCIDA
    finally:
        await primero.disconnect()
        await segundo.disconnect()


@ejecutar_async
async def test_transaccion_revertida_no_publica_evento():
    jugador, _, _, cancha, dia = await _sync(_contexto, "ws-owner-rollback@example.test")
    url = _url(cancha.pk, desde=dia.isoformat(), hasta=dia.isoformat())
    comunicador = _comunicador(url)
    assert (await comunicador.connect())[0] is True
    try:
        def revertir():
            from django.db import transaction

            try:
                with transaction.atomic():
                    crear_retencion(jugador, cancha.pk, dia, datetime.strptime("19:00", "%H:%M").time(), 1, uuid4())
                    raise RuntimeError("rollback de prueba")
            except RuntimeError:
                return

        await _sync(revertir)
        assert await comunicador.receive_nothing(timeout=0.2)
        assert not await _sync(Reserva.objects.filter(cancha=cancha).exists)
    finally:
        await comunicador.disconnect()


@ejecutar_async
async def test_suscripcion_privada_solo_permite_membresia_autorizada():
    propietario, _, _, cancha, dia = await _sync(_contexto, "ws-private-owner@example.test")
    await _sync(Cancha.objects.filter(pk=cancha.pk).update, publicada=False)
    almacen = await _sync(_sesion, propietario)
    url = _url(cancha.pk, desde=dia.isoformat(), hasta=dia.isoformat())
    autorizado = _comunicador(url, propietario, almacen)
    assert (await autorizado.connect())[0] is True
    await autorizado.disconnect()

    intruso, _, _, _, _ = await _sync(_contexto, "ws-owner-otra-empresa@example.test")
    rechazado = _comunicador(url, intruso, await _sync(_sesion, intruso))
    conectado, _ = await rechazado.connect()
    assert conectado is False

    anonimo = _comunicador(url)
    conectado, _ = await anonimo.connect()
    assert conectado is False


@ejecutar_async
async def test_revalida_sesion_expirada_y_cierra_conexion_privada():
    propietario, _, _, cancha, dia = await _sync(_contexto, "ws-session-owner@example.test")
    await _sync(Cancha.objects.filter(pk=cancha.pk).update, publicada=False)
    almacen = await _sync(_sesion, propietario)
    url = _url(cancha.pk, desde=dia.isoformat(), hasta=dia.isoformat())
    comunicador = _comunicador(url, propietario, almacen)
    assert (await comunicador.connect())[0] is True
    try:
        await _sync(almacen.delete)
        await _sync(
            programar_cambio_disponibilidad, cancha.pk, dia, "horario_actualizado"
        )
        salida = await comunicador.receive_output(timeout=2)
        assert salida["type"] == "websocket.close"
        assert salida["code"] == 4401
    finally:
        await comunicador.disconnect()


@ejecutar_async
async def test_canchas_distintas_no_reciben_eventos_ajenos():
    jugador_a, _, _, cancha_a, dia = await _sync(_contexto, "ws-court-a@example.test")
    _, _, _, cancha_b, _ = await _sync(_contexto, "ws-court-b@example.test", dia=dia)
    cliente_a = _comunicador(_url(cancha_a.pk, desde=dia.isoformat(), hasta=dia.isoformat()))
    cliente_b = _comunicador(_url(cancha_b.pk, desde=dia.isoformat(), hasta=dia.isoformat()))
    assert (await cliente_a.connect())[0] is True
    assert (await cliente_b.connect())[0] is True
    try:
        await _crear(jugador_a, cancha_a, dia)
        mensaje = await cliente_a.receive_json_from(timeout=2)
        assert mensaje["cancha_id"] == cancha_a.pk
        assert await cliente_b.receive_nothing(timeout=0.2)
    finally:
        await cliente_a.disconnect()
        await cliente_b.disconnect()


@ejecutar_async
async def test_rechaza_query_invalida_y_mensajes_de_cliente():
    _, _, _, cancha, dia = await _sync(_contexto, "ws-invalid-owner@example.test")
    fecha = dia.isoformat()
    invalido = _comunicador(f"/ws/disponibilidad/?canchas={cancha.pk}&desde={fecha}")
    conectado, _ = await invalido.connect()
    assert conectado is False

    comunicador = _comunicador(_url(cancha.pk, desde=fecha, hasta=fecha))
    assert (await comunicador.connect())[0] is True
    await comunicador.send_to(text_data='{"tipo":"crear_reserva"}')
    salida = await comunicador.receive_output(timeout=2)
    assert salida["type"] == "websocket.close"
    assert salida["code"] == 4400
    await comunicador.disconnect()


@ejecutar_async
async def test_origen_websocket_no_permitido_se_rechaza_en_asgi():
    _, _, _, cancha, dia = await _sync(_contexto, "ws-origin-owner@example.test")
    fecha = dia.isoformat()
    url = _url(cancha.pk, desde=fecha, hasta=fecha)
    comunicador = WebsocketCommunicator(
        application, url, headers=[(b"origin", b"https://sitio-ajeno.example")]
    )
    conectado, _ = await comunicador.connect()
    assert conectado is False


def test_redis_real_disponible_si_se_configura_en_entorno(monkeypatch):
    redis_url = os.getenv("ALTOQUE_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Define ALTOQUE_TEST_REDIS_URL para ejecutar esta prueba de integración Redis.")

    async def intercambiar():
        capa = get_channel_layer()
        nombre = "disponibilidad-prueba-redis"
        canal = await capa.new_channel()
        await capa.group_add(nombre, canal)
        await capa.group_send(nombre, {"type": "prueba.evento", "ok": True})
        recibido = await capa.receive(canal)
        await capa.group_discard(nombre, canal)
        return recibido

    with override_settings(CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_url]},
        },
    }):
        channel_layers.backends.clear()
        try:
            assert asyncio.run(intercambiar())["ok"] is True
        finally:
            channel_layers.backends.clear()
