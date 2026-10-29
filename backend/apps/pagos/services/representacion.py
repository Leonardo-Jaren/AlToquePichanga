import re
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Sum
from django.utils import timezone

from apps.pagos.models import EstadoPagoReserva, MetodoPagoSede, PagoReserva
from apps.reservas.models import EstadoReserva, Reserva

ESTADOS_CON_PLAZO = (
    EstadoReserva.RETENIDA,
    EstadoReserva.PENDIENTE_PAGO,
    EstadoReserva.PENDIENTE_VERIFICACION,
    EstadoReserva.PENDIENTE_CONFIRMACION,
)


def importe_pagado(reserva: Reserva) -> Decimal:
    total = PagoReserva.objects.filter(
        reserva=reserva, estado=EstadoPagoReserva.APROBADO,
    ).aggregate(total=Sum("importe_verificado"))["total"]
    return total or Decimal("0.00")


def fecha_limite(reserva: Reserva):
    return reserva.revision_pago_vence_en or reserva.retencion_vence_en


def datos_metodo(metodo: MetodoPagoSede, request=None) -> dict:
    qr_url = metodo.imagen_qr.url if metodo.imagen_qr else None
    if qr_url and request:
        qr_url = request.build_absolute_uri(qr_url)
    return {
        "id": metodo.pk, "tipo": metodo.tipo, "etiqueta": metodo.get_tipo_display(),
        "titular": metodo.titular, "numero_cuenta": metodo.numero_cuenta,
        "banco": metodo.banco, "cci": metodo.cci, "instrucciones": metodo.instrucciones,
        "imagen_qr_url": qr_url, "activo": metodo.activo,
    }


def datos_historial(pago: PagoReserva) -> list[dict]:
    return [{
        "estado_anterior": item.estado_anterior,
        "estado_nuevo": item.estado_nuevo,
        "motivo": item.motivo,
        "actor": item.actor.get_full_name() or item.actor.username if item.actor else None,
        "creado_en": item.creado_en,
    } for item in pago.historial.select_related("actor")]


def datos_pago(pago: PagoReserva, request=None) -> dict:
    return {
        "id": pago.pk, "codigo_reserva": pago.reserva.codigo,
        "estado": pago.estado, "tipo": pago.tipo,
        "importe_solicitado": pago.importe_solicitado,
        "importe_verificado": pago.importe_verificado,
        "referencia": pago.referencia, "observacion_jugador": pago.observacion_jugador,
        "motivo_revision": pago.motivo_revision,
        "creado_en": pago.creado_en, "declarado_en": pago.declarado_en,
        "revisado_en": pago.revisado_en,
        "requiere_conciliacion": pago.requiere_conciliacion,
        "metodo": datos_metodo(pago.metodo, request),
        "historial": datos_historial(pago),
    }


def url_whatsapp(reserva: Reserva, importe_a_verificar: Decimal | None = None) -> str | None:
    telefono = re.sub(r"\D", "", reserva.cancha.sede.whatsapp_contacto or "")
    if not 8 <= len(telefono) <= 15:
        return None
    inicio = timezone.localtime(reserva.inicio).strftime("%d/%m/%Y %H:%M")
    fin = timezone.localtime(reserva.fin).strftime("%H:%M")
    texto = (
        f"Hola, envío el comprobante de la reserva {reserva.codigo} en "
        f"{reserva.cancha.sede.nombre}, {reserva.cancha.nombre}, {inicio}-{fin}. "
        f"Monto a verificar: S/ {(importe_a_verificar or reserva.importe_total):.2f}. "
        "Adjuntaré la captura manualmente."
    )
    return f"https://wa.me/{telefono}?{urlencode({'text': texto})}"


def datos_reserva_pago(reserva: Reserva, request=None) -> dict:
    pagos = list(reserva.pagos_reserva.select_related("metodo").prefetch_related("historial__actor"))
    pagado = importe_pagado(reserva)
    pago_activo = next((
        pago for pago in pagos if pago.estado in {
            EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION,
        }
    ), None)
    metodos = MetodoPagoSede.objects.filter(sede_id=reserva.cancha.sede_id, activo=True)
    return {
        "codigo": reserva.codigo, "cancha": reserva.cancha.nombre,
        "sede": reserva.cancha.sede.nombre, "inicio": reserva.inicio, "fin": reserva.fin,
        "estado_reserva": reserva.estado, "moneda": reserva.moneda,
        "importe_total": reserva.importe_total, "adelanto_minimo": reserva.adelanto_minimo,
        "importe_pagado": pagado,
        "saldo_pendiente": max(reserva.importe_total - pagado, Decimal("0.00")),
        "vence_en": fecha_limite(reserva) if reserva.estado in ESTADOS_CON_PLAZO else None,
        "whatsapp_url": url_whatsapp(
            reserva, pago_activo.importe_solicitado if pago_activo else None,
        ),
        "metodos": [datos_metodo(metodo, request) for metodo in metodos.order_by("tipo")],
        "pagos": [datos_pago(pago, request) for pago in pagos],
    }


def datos_pago_administrativo(pago: PagoReserva, request=None) -> dict:
    resultado = datos_pago(pago, request)
    reserva = pago.reserva
    resultado.update({
        "empresa": reserva.cancha.sede.empresa.nombre_visible,
        "sede": reserva.cancha.sede.nombre,
        "cancha": reserva.cancha.nombre,
        "jugador": {
            "nombre": reserva.jugador.get_full_name() or reserva.jugador.username,
            "correo": reserva.jugador.email,
        },
    })
    return resultado
