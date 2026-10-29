from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.reservas.models import EstadoReserva
from apps.reservas.models.bloque import BloqueReserva
from apps.tarifas.services.disponibilidad import (
    consultar_disponibilidad_tarifada,
    consultar_disponibilidad_tarifada_publica,
)

ESTADOS_QUE_OCUPAN = (
    EstadoReserva.RETENIDA,
    EstadoReserva.PENDIENTE_PAGO,
    EstadoReserva.PENDIENTE_VERIFICACION,
    EstadoReserva.PENDIENTE_CONFIRMACION,
    EstadoReserva.CONFIRMADA,
)
ZONA_HORARIA = ZoneInfo(settings.TIME_ZONE)


def horario_reservado(cancha_id: int, inicio_local: datetime, duracion_horas: int) -> bool:
    inicio = timezone.make_aware(inicio_local, ZONA_HORARIA)
    fin = inicio + timedelta(hours=duracion_horas)
    return BloqueReserva.objects.filter(
        cancha_id=cancha_id,
        liberado_en__isnull=True,
        inicio__lt=fin,
        fin__gt=inicio,
        reserva__estado__in=ESTADOS_QUE_OCUPAN,
    ).filter(_reservas_no_vencidas()).exists()


def consultar_disponibilidad_reservable(
    cancha, desde: date, hasta: date, *, publica: bool = False, usuario=None
) -> dict:
    resultado = (
        consultar_disponibilidad_tarifada_publica(cancha, desde, hasta)
        if publica
        else consultar_disponibilidad_tarifada(usuario, cancha.pk, desde, hasta)
    )
    ahora = timezone.now()
    inicio_rango = timezone.make_aware(datetime.combine(desde, time.min))
    fin_rango = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min))
    reservas = BloqueReserva.objects.filter(
        cancha=cancha,
        liberado_en__isnull=True,
        inicio__lt=fin_rango,
        fin__gt=inicio_rango,
        reserva__estado__in=ESTADOS_QUE_OCUPAN,
    ).filter(_reservas_no_vencidas(ahora)).values_list("inicio", "fin", "reserva__estado")
    intervalos = list(reservas)

    for bloque in resultado["bloques"]:
        inicio = datetime.fromisoformat(bloque["fecha_inicio"])
        fin = datetime.fromisoformat(bloque["fecha_fin"])
        ocupado = next(
            (estado for inicio_activo, fin_activo, estado in intervalos
             if inicio_activo < fin and fin_activo > inicio),
            None,
        )
        bloque["estado_reserva"] = ocupado
        bloque["reservable"] = bool(
            bloque.get("habilitada_operativamente")
            and bloque.get("tarifa_estado") == "configurada"
            and ocupado is None
        )
        if ocupado:
            bloque.update({
                "estado": "retenida" if ocupado == EstadoReserva.RETENIDA else "ocupada",
                "habilitada_operativamente": False,
                "motivo": "Horario retenido temporalmente." if ocupado == EstadoReserva.RETENIDA
                else "Horario reservado.",
            })

    resultado["considera_reservas"] = True
    return resultado


def _reservas_no_vencidas(ahora=None):
    ahora = ahora or timezone.now()
    return Q(reserva__estado=EstadoReserva.CONFIRMADA) | Q(
        reserva__revision_pago_vence_en__gt=ahora
    ) | Q(
        reserva__revision_pago_vence_en__isnull=True,
        reserva__retencion_vence_en__gt=ahora,
    )
