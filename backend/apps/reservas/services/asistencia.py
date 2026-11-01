"""Consulta y registro de ingreso dentro del alcance del empleado."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.services.auditoria import auditar
from apps.pagos.services.representacion import importe_pagado
from apps.reservas.models import AsistenciaReserva, EstadoReserva, Reserva
from apps.reservas.services.ticket import leer_token_ticket


def _codigo(valor: str, tipo: str) -> str:
    return leer_token_ticket(valor) if tipo == "qr" else valor.strip().upper()


def _reservas_autorizadas(usuario):
    return Reserva.objects.filter(cancha__in=canchas_visibles(usuario)).exclude(
        jugador=usuario,
    ).select_related("cancha__sede__empresa")


def _comprobar_estado(reserva: Reserva) -> None:
    ahora = timezone.now()
    if reserva.estado != EstadoReserva.CONFIRMADA:
        raise ValidationError({"estado": "La reserva no está confirmada o ya no es válida."})
    if not reserva.inicio <= ahora < reserva.fin:
        raise ValidationError({"horario": "El horario de esta reserva no está en curso."})


def consultar_ingreso(usuario, valor: str, tipo: str) -> dict:
    reserva = get_object_or_404(_reservas_autorizadas(usuario), codigo=_codigo(valor, tipo))
    _comprobar_estado(reserva)
    asistencia = AsistenciaReserva.objects.filter(reserva=reserva).first()
    auditar(usuario, "consultar_ingreso", "reserva", reserva.pk, reserva.cancha.sede.empresa)
    return {
        "codigo": reserva.codigo, "sede": reserva.cancha.sede.nombre,
        "cancha": reserva.cancha.nombre, "inicio": reserva.inicio, "fin": reserva.fin,
        "saldo_pendiente": max(reserva.importe_total - importe_pagado(reserva), 0),
        "moneda": reserva.moneda, "asistencia_registrada": asistencia is not None,
        "registrada_en": asistencia.registrada_en if asistencia else None,
    }


@transaction.atomic
def registrar_ingreso(usuario, valor: str, tipo: str) -> tuple[dict, bool]:
    codigo = _codigo(valor, tipo)
    reserva = get_object_or_404(_reservas_autorizadas(usuario).select_for_update(of=("self",)), codigo=codigo)
    _comprobar_estado(reserva)
    asistencia, creada = AsistenciaReserva.objects.get_or_create(reserva=reserva, defaults={"empleado": usuario})
    if creada:
        auditar(usuario, "registrar_ingreso", "reserva", reserva.pk, reserva.cancha.sede.empresa)
    return {"codigo": reserva.codigo, "registrada_en": asistencia.registrada_en, "ya_registrada": not creada}, creada
