from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.canchas.models import Cancha, EstadoCancha
from apps.empresas.models import EstadoEmpresa
from apps.reservas.models import BloqueReserva, EstadoReserva, Reserva
from apps.reservas.services.disponibilidad import ESTADOS_QUE_OCUPAN
from apps.reservas.services.estados import cambiar_estado, cambiar_estado_inicial
from apps.reservas.services.eventos import programar_cambio_intervalo
from apps.reservas.services.retenciones import _vencer_de_cancha
from apps.tarifas.services.disponibilidad import previsualizar_precio_para_cancha

ZONA_HORARIA = ZoneInfo(settings.TIME_ZONE)


class HorarioNoDisponible(APIException):
    status_code = 409
    default_detail = "Ese horario acaba de dejar de estar disponible. Actualiza el calendario y elige otro bloque."
    default_code = "horario_no_disponible"


def _fechas_solicitadas(fecha: date, hora_inicio: time, duracion: int):
    inicio_local = timezone.make_aware(datetime.combine(fecha, hora_inicio), ZONA_HORARIA)
    return inicio_local, inicio_local + timedelta(hours=duracion)


def _coincide_solicitud(reserva: Reserva, cancha_id: int, inicio, fin, duracion: int) -> bool:
    return (
        reserva.cancha_id == cancha_id
        and reserva.inicio == inicio
        and reserva.fin == fin
        and reserva.duracion_horas == duracion
    )


def _revisar_reintento(jugador, clave: UUID, cancha_id: int, inicio, fin, duracion):
    reserva = Reserva.objects.filter(jugador=jugador, clave_idempotencia=clave).first()
    if not reserva:
        return None
    if not _coincide_solicitud(reserva, cancha_id, inicio, fin, duracion):
        raise ValidationError({"clave_idempotencia": "Esta clave ya identifica otra solicitud."})
    return reserva


def _crear_bloques(reserva: Reserva, cancha: Cancha, inicio, fin) -> None:
    bloques = []
    cursor = inicio
    while cursor < fin:
        siguiente = cursor + timedelta(hours=1)
        bloques.append(BloqueReserva(
            reserva=reserva, cancha=cancha, inicio=cursor, fin=siguiente,
        ))
        cursor = siguiente
    BloqueReserva.objects.bulk_create(bloques)


def _intervalo_ocupado(cancha_id: int, inicio, fin) -> bool:
    return BloqueReserva.objects.filter(
        cancha_id=cancha_id,
        liberado_en__isnull=True,
        inicio__lt=fin,
        fin__gt=inicio,
        reserva__estado__in=ESTADOS_QUE_OCUPAN,
    ).exists()


def _crear_dentro_transaccion(jugador, cancha_id, fecha, hora_inicio, duracion, clave):
    inicio, fin = _fechas_solicitadas(fecha, hora_inicio, duracion)
    cancha = Cancha.objects.select_for_update().select_related(
        "sede", "sede__empresa"
    ).filter(pk=cancha_id).first()
    if not cancha:
        raise ValidationError({"cancha_id": "La cancha indicada no está disponible para reservar."})
    reintento = _revisar_reintento(jugador, clave, cancha_id, inicio, fin, duracion)
    if reintento:
        return reintento, False

    empresa = cancha.sede.empresa
    if (not cancha.publicada or cancha.estado != EstadoCancha.ACTIVA
            or not cancha.sede.activa or not empresa.activa
            or empresa.estado != EstadoEmpresa.ACTIVA):
        raise ValidationError({"cancha_id": "Esta cancha no está habilitada para nuevas reservas."})
    ahora = timezone.now()
    if inicio <= ahora:
        raise ValidationError({"hora_inicio": "Elige un horario que todavía no haya comenzado."})

    _vencer_de_cancha(cancha.pk, ahora)
    if _intervalo_ocupado(cancha.pk, inicio, fin):
        raise HorarioNoDisponible()

    cotizacion = previsualizar_precio_para_cancha(cancha, fecha, hora_inicio, duracion)
    total = Decimal(cotizacion["total"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    adelanto = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    minutos = getattr(settings, "RESERVA_RETENCION_MINUTOS", 15)
    vence = ahora + timedelta(minutes=minutos)
    reserva = Reserva.objects.create(
        jugador=jugador,
        cancha=cancha,
        inicio=inicio,
        fin=fin,
        duracion_horas=duracion,
        importe_total=total,
        adelanto_minimo=adelanto,
        moneda=cotizacion["moneda"],
        estado=EstadoReserva.RETENIDA,
        retencion_vence_en=vence,
        cotizacion_aplicada=cotizacion,
        clave_idempotencia=clave,
    )
    cambiar_estado_inicial(reserva, "El jugador solicitó la retención temporal.", jugador)
    _crear_bloques(reserva, cancha, inicio, fin)
    programar_cambio_intervalo(cancha.pk, inicio, fin, "retencion_creada")
    return reserva, True


def crear_retencion(jugador, cancha_id: int, fecha: date, hora_inicio: time,
                    duracion: int, clave: UUID):
    if not 1 <= duracion <= 24:
        raise ValidationError({"duracion_horas": "La duración debe estar entre 1 y 24 horas."})
    inicio, fin = _fechas_solicitadas(fecha, hora_inicio, duracion)
    reintento = _revisar_reintento(jugador, clave, cancha_id, inicio, fin, duracion)
    if reintento:
        return reintento, False
    try:
        with transaction.atomic():
            return _crear_dentro_transaccion(
                jugador, cancha_id, fecha, hora_inicio, duracion, clave
            )
    except IntegrityError as error:
        reintento = _revisar_reintento(jugador, clave, cancha_id, inicio, fin, duracion)
        if reintento:
            return reintento, False
        if _intervalo_ocupado(cancha_id, inicio, fin):
            raise HorarioNoDisponible() from error
        raise


@transaction.atomic
def cancelar_retencion(jugador, codigo: str):
    reserva = Reserva.objects.filter(jugador=jugador, codigo=codigo).select_related("cancha").first()
    if not reserva:
        return None
    Cancha.objects.select_for_update().get(pk=reserva.cancha_id)
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    ahora = timezone.now()
    if reserva.estado == EstadoReserva.RETENIDA and reserva.retencion_vence_en <= ahora:
        cambiar_estado(reserva, EstadoReserva.VENCIDA, "Venció el plazo de retención.")
        reserva.bloques.filter(liberado_en__isnull=True).update(liberado_en=ahora)
        motivo = "retencion_vencida"
    elif reserva.estado == EstadoReserva.RETENIDA:
        cambiar_estado(reserva, EstadoReserva.CANCELADA, "El jugador canceló la retención.", jugador)
        reserva.bloques.filter(liberado_en__isnull=True).update(liberado_en=ahora)
        motivo = "retencion_cancelada"
    else:
        raise ValidationError({"estado": "Solo puedes cancelar una retención que siga vigente."})
    programar_cambio_intervalo(reserva.cancha_id, reserva.inicio, reserva.fin, motivo)
    return reserva
