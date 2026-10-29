"""Medios y solicitudes locales para probar pagos sin usar cuentas reales."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from apps.pagos.models import (
    EstadoPagoReserva,
    HistorialPagoReserva,
    MetodoPagoSede,
    PagoReserva,
    TipoMetodoPago,
    TipoPagoReserva,
)
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.usuarios.services.datos_demo import MARCA, identidad_demo


def _clave_pago(reserva: Reserva, clave: str):
    return uuid5(NAMESPACE_URL, identidad_demo(f"pago:{reserva.pk}:{clave}"))


def _medios_demo(sedes: dict) -> dict[tuple[str, str], MetodoPagoSede]:
    medios = {}
    for sede_clave, sede in sedes.items():
        for tipo in TipoMetodoPago.values:
            medio = MetodoPagoSede.objects.filter(sede=sede, tipo=tipo).first()
            if medio:
                if not medio.titular.startswith(MARCA):
                    raise CommandError(
                        f"La sede demo {sede.nombre} tiene un medio ajeno; no se modificó."
                    )
                medios[(sede_clave, tipo)] = medio
                continue
            transferencia = tipo == TipoMetodoPago.TRANSFERENCIA
            medios[(sede_clave, tipo)] = MetodoPagoSede.objects.create(
                sede=sede, tipo=tipo, titular=f"{MARCA} Titular ficticio",
                numero_cuenta="00000000000", banco="Banco ficticio" if transferencia else "",
                cci="00000000000000000000" if transferencia else "",
                instrucciones="Datos ficticios locales; no realizar transferencias.", activo=True,
            )
    return medios


def _historial(pago: PagoReserva, estados: list[str], jugador, revisor=None) -> None:
    for indice, estado in enumerate(estados):
        HistorialPagoReserva.objects.get_or_create(
            pago=pago, estado_anterior=estados[indice - 1] if indice else "",
            estado_nuevo=estado,
            defaults={
                "motivo": "Registro ficticio local para comprobar la pantalla de pagos.",
                "actor": revisor if estado in {EstadoPagoReserva.APROBADO, EstadoPagoReserva.RECHAZADO} else jugador,
                "datos": {"fixture": identidad_demo(f"pago:{pago.clave_idempotencia}")},
            },
        )


def _crear_pago(
    reserva: Reserva,
    metodo: MetodoPagoSede,
    clave: str,
    tipo: str,
    importe: Decimal,
    estado: str,
    jugador,
    revisor=None,
    *,
    importe_verificado: Decimal = Decimal("0.00"),
    conciliacion: bool = False,
) -> tuple[PagoReserva, bool]:
    idempotencia = _clave_pago(reserva, clave)
    pago = PagoReserva.objects.filter(clave_idempotencia=idempotencia).first()
    if pago:
        if pago.reserva_id != reserva.pk or pago.metodo_id != metodo.pk or pago.tipo != tipo:
            raise CommandError("La clave de un pago demo colisionó con un registro ajeno.")
        return pago, False
    ahora = timezone.now()
    pago = PagoReserva.objects.create(
        reserva=reserva, metodo=metodo, tipo=tipo, estado=estado,
        importe_solicitado=importe, importe_verificado=importe_verificado,
        referencia=f"DEMO-{clave.upper()}", observacion_jugador="[DEMO ALTOQUE] Comprobante ficticio.",
        motivo_revision=("[DEMO ALTOQUE] Revisión local." if revisor else ""),
        clave_idempotencia=idempotencia, requiere_conciliacion=conciliacion,
        creado_en=ahora, declarado_en=ahora if estado != EstadoPagoReserva.PENDIENTE_PAGO else None,
        revisado_en=ahora if revisor else None, revisor=revisor,
    )
    secuencia = {
        EstadoPagoReserva.PENDIENTE_PAGO: [EstadoPagoReserva.PENDIENTE_PAGO],
        EstadoPagoReserva.PENDIENTE_REVISION: [EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION],
        EstadoPagoReserva.APROBADO: [EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION, EstadoPagoReserva.APROBADO],
        EstadoPagoReserva.RECHAZADO: [EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION, EstadoPagoReserva.RECHAZADO],
        EstadoPagoReserva.VENCIDO: [EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.VENCIDO],
        EstadoPagoReserva.PAGO_TARDIO: [EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PAGO_TARDIO],
    }[estado]
    _historial(pago, secuencia, jugador, revisor)
    return pago, True


def _preparar_reserva_revision(reserva: Reserva, actor, ahora) -> bool:
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado not in {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO,
        EstadoReserva.PENDIENTE_VERIFICACION, EstadoReserva.PENDIENTE_CONFIRMACION,
    }:
        return False
    vence = reserva.revision_pago_vence_en or reserva.retencion_vence_en
    if vence <= ahora:
        return False
    if not reserva.revision_pago_extendida:
        reserva.revision_pago_vence_en = ahora + timedelta(minutes=settings.RESERVA_REVISION_PAGO_MINUTOS)
        reserva.revision_pago_extendida = True
        reserva.save(update_fields=["revision_pago_vence_en", "revision_pago_extendida", "actualizada_en"])
    if reserva.estado == EstadoReserva.RETENIDA:
        cambiar_estado(reserva, EstadoReserva.PENDIENTE_PAGO, "Inicio de flujo demo de pago.", actor)
    if reserva.estado == EstadoReserva.PENDIENTE_CONFIRMACION:
        cambiar_estado(reserva, EstadoReserva.PENDIENTE_PAGO, "Solicitud demo del saldo restante.", actor)
    return True


@transaction.atomic
def crear_pagos_demo(sedes: dict, reservas: dict[str, Reserva], usuarios: dict) -> int:
    """Crea únicamente métodos ficticios y pagos ligados a reservas demo estables."""
    medios = _medios_demo(sedes)
    jugador = usuarios["jugador"]
    cajero = usuarios["cajero_a"]
    ahora = timezone.now()
    reserva_a = reservas["retencion-una-hora"]
    reserva_b = reservas["retencion-multihora-empresa-b"]
    reserva_vencida = reservas["retencion-vencida-liberada"]
    existe_saldo = PagoReserva.objects.filter(
        clave_idempotencia=_clave_pago(reserva_a, "saldo-en-revision"),
    ).exists()
    existe_total = PagoReserva.objects.filter(
        clave_idempotencia=_clave_pago(reserva_b, "pago-total-enviado"),
    ).exists()
    activa_a = _preparar_reserva_revision(reserva_a, jugador, ahora) if not existe_saldo else False
    activa_b = _preparar_reserva_revision(reserva_b, jugador, ahora) if not existe_total else False

    _crear_pago(
        reserva_a, medios[("sede_a_centro", TipoMetodoPago.YAPE)], "adelanto-rechazado",
        TipoPagoReserva.ADELANTO, reserva_a.adelanto_minimo, EstadoPagoReserva.RECHAZADO,
        jugador, cajero,
    )
    reserva_a.refresh_from_db()
    _crear_pago(
        reserva_a, medios[("sede_a_centro", TipoMetodoPago.PLIN)], "adelanto-aprobado",
        TipoPagoReserva.ADELANTO, reserva_a.adelanto_minimo, EstadoPagoReserva.APROBADO,
        jugador, cajero, importe_verificado=reserva_a.adelanto_minimo,
        conciliacion=reserva_a.estado == EstadoReserva.VENCIDA,
    )
    if activa_a:
        _pago_saldo, saldo_creado = _crear_pago(
            reserva_a, medios[("sede_a_centro", TipoMetodoPago.YAPE)], "saldo-en-revision",
            TipoPagoReserva.SALDO, reserva_a.importe_total - reserva_a.adelanto_minimo,
            EstadoPagoReserva.PENDIENTE_REVISION, jugador,
        )
        if saldo_creado:
            reserva_a.refresh_from_db()
            if reserva_a.estado == EstadoReserva.PENDIENTE_PAGO:
                cambiar_estado(reserva_a, EstadoReserva.PENDIENTE_CONFIRMACION, "Adelanto demo verificado.", cajero)
            if reserva_a.estado == EstadoReserva.PENDIENTE_CONFIRMACION:
                cambiar_estado(reserva_a, EstadoReserva.PENDIENTE_PAGO, "Saldo demo declarado.", jugador)
            if reserva_a.estado == EstadoReserva.PENDIENTE_PAGO:
                cambiar_estado(reserva_a, EstadoReserva.PENDIENTE_VERIFICACION, "Saldo demo en revisión.", jugador)

    importe_total_b = reserva_b.importe_total
    estado_b = EstadoPagoReserva.PENDIENTE_PAGO if activa_b else EstadoPagoReserva.VENCIDO
    _crear_pago(
        reserva_b, medios[("sede_b_centro", TipoMetodoPago.TRANSFERENCIA)], "pago-total-enviado",
        TipoPagoReserva.TOTAL, importe_total_b, estado_b, jugador,
    )
    _crear_pago(
        reserva_vencida, medios[("sede_a_centro", TipoMetodoPago.YAPE)], "comprobante-tardio",
        TipoPagoReserva.ADELANTO, reserva_vencida.adelanto_minimo,
        EstadoPagoReserva.PAGO_TARDIO, jugador,
        conciliacion=True,
    )
    return len(medios)
