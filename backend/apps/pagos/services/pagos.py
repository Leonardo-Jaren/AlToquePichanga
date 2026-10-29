from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.models import Cancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.models import RegistroAuditoria
from apps.empresas.services.auditoria import auditar
from apps.pagos.models import (
    EstadoPagoReserva,
    HistorialPagoReserva,
    MetodoPagoSede,
    PagoReserva,
    TipoPagoReserva,
)
from apps.pagos.services.representacion import (
    datos_reserva_pago,
    fecha_limite,
    importe_pagado,
    url_whatsapp,
)
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.reservas.services.eventos import programar_cambio_intervalo
from apps.reservas.services.retenciones import _vencer_de_cancha

PAGOS_ACTIVOS = (EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION)
ESTADOS_CON_PLAZO = (
    EstadoReserva.RETENIDA,
    EstadoReserva.PENDIENTE_PAGO,
    EstadoReserva.PENDIENTE_VERIFICACION,
    EstadoReserva.PENDIENTE_CONFIRMACION,
)


def _reserva_bloqueada(jugador, codigo: str) -> Reserva | None:
    reserva = Reserva.objects.filter(jugador=jugador, codigo=codigo).only("pk", "cancha_id").first()
    if reserva is None:
        return None
    Cancha.objects.select_for_update().get(pk=reserva.cancha_id)
    return Reserva.objects.select_for_update().select_related(
        "cancha", "cancha__sede", "cancha__sede__empresa", "jugador",
    ).get(pk=reserva.pk, jugador=jugador)


def _registrar_estado(pago: PagoReserva, estado: str, actor, motivo: str, datos=None) -> None:
    anterior = pago.estado
    pago.estado = estado
    pago.save(update_fields=["estado", "declarado_en", "revisado_en", "revisor", "referencia",
                             "observacion_jugador", "motivo_revision", "importe_verificado",
                             "requiere_conciliacion"])
    HistorialPagoReserva.objects.create(
        pago=pago, estado_anterior=anterior, estado_nuevo=estado,
        motivo=motivo, actor=actor, datos=datos or {},
    )


def _actualizar_auditoria(actor, accion: str, pago: PagoReserva, datos=None) -> None:
    auditar(
        actor, accion, "pago_reserva", pago.pk,
        pago.reserva.cancha.sede.empresa, {"codigo_reserva": pago.reserva.codigo, **(datos or {})},
    )


def consultar_pago_propietario(jugador, codigo: str, request=None) -> dict | None:
    reserva = Reserva.objects.filter(jugador=jugador, codigo=codigo).select_related(
        "cancha", "cancha__sede", "cancha__sede__empresa",
    ).first()
    return datos_reserva_pago(reserva, request) if reserva else None


@transaction.atomic
def crear_solicitud_pago(jugador, codigo: str, tipo: str, metodo_id: int, clave) -> PagoReserva | None:
    reserva = _reserva_bloqueada(jugador, codigo)
    if reserva is None:
        return None
    pago_reintentado = PagoReserva.objects.select_for_update().filter(clave_idempotencia=clave).first()
    if pago_reintentado:
        if pago_reintentado.reserva_id != reserva.pk or pago_reintentado.tipo != tipo or pago_reintentado.metodo_id != metodo_id:
            raise ValidationError({"clave_idempotencia": "Esta clave ya identifica otra solicitud de pago."})
        return pago_reintentado
    ahora = timezone.now()
    if reserva.estado in ESTADOS_CON_PLAZO and fecha_limite(reserva) <= ahora:
        _vencer_de_cancha(reserva.cancha_id, ahora)
        return None
    metodo = MetodoPagoSede.objects.select_for_update().filter(
        pk=metodo_id, sede_id=reserva.cancha.sede_id, activo=True,
    ).first()
    if metodo is None:
        raise ValidationError({"metodo_id": "Ese medio de pago no está activo para esta sede."})
    if url_whatsapp(reserva) is None:
        raise ValidationError({
            "whatsapp": "La sede debe configurar un número oficial de WhatsApp antes de recibir comprobantes.",
        })
    existente = PagoReserva.objects.select_for_update().filter(reserva=reserva, estado__in=PAGOS_ACTIVOS).first()
    if existente:
        if existente.clave_idempotencia == clave:
            return existente
        raise ValidationError({"pago": "Ya hay un pago pendiente de enviar o revisar para esta reserva."})
    if reserva.estado not in {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO, EstadoReserva.PENDIENTE_CONFIRMACION,
    }:
        raise ValidationError({"estado": "Esta reserva no admite una nueva solicitud de pago."})
    pagado = importe_pagado(reserva)
    saldo = reserva.importe_total - pagado
    if saldo <= Decimal("0.00"):
        raise ValidationError({"tipo": "La reserva ya tiene el importe total aprobado."})
    if tipo == TipoPagoReserva.ADELANTO:
        if pagado:
            raise ValidationError({"tipo": "Para continuar con un pago aprobado, solicita el saldo."})
        importe = reserva.adelanto_minimo
    elif tipo == TipoPagoReserva.TOTAL:
        if pagado:
            raise ValidationError({"tipo": "El saldo se solicita con la opción de pago restante."})
        importe = reserva.importe_total
    else:
        if pagado < reserva.adelanto_minimo:
            raise ValidationError({"tipo": "Primero debe aprobarse el adelanto mínimo."})
        importe = saldo
    pago = PagoReserva.objects.create(
        reserva=reserva, metodo=metodo, tipo=tipo, importe_solicitado=importe,
        clave_idempotencia=clave,
    )
    HistorialPagoReserva.objects.create(
        pago=pago, estado_anterior="", estado_nuevo=pago.estado,
        motivo="Se generó una solicitud manual de pago.", actor=jugador,
        datos={"importe_solicitado": str(importe), "tipo": tipo},
    )
    if reserva.estado in {EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_CONFIRMACION}:
        cambiar_estado(reserva, EstadoReserva.PENDIENTE_PAGO, "El jugador inició el pago manual.", jugador)
    _actualizar_auditoria(jugador, "solicitar_pago_reserva", pago, {"tipo": tipo})
    return pago


@transaction.atomic
def declarar_comprobante(jugador, codigo: str, pago_id: int, referencia: str, observacion: str):
    reserva = _reserva_bloqueada(jugador, codigo)
    if reserva is None:
        return None, False
    pago = PagoReserva.objects.select_for_update().select_related("metodo").filter(
        pk=pago_id, reserva=reserva,
    ).first()
    if pago is None:
        return None, False
    ahora = timezone.now()
    if pago.estado == EstadoPagoReserva.PENDIENTE_REVISION:
        return pago, False
    if pago.estado not in {EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.VENCIDO}:
        raise ValidationError({"estado": "Este pago ya no admite declarar un comprobante."})
    vencido = fecha_limite(reserva) <= ahora or reserva.estado == EstadoReserva.VENCIDA
    if vencido:
        if reserva.estado in ESTADOS_CON_PLAZO:
            _vencer_de_cancha(reserva.cancha_id, ahora)
        pago.refresh_from_db()
        pago.referencia = referencia.strip()
        pago.observacion_jugador = observacion.strip()
        pago.declarado_en = ahora
        _registrar_estado(
            pago, EstadoPagoReserva.PAGO_TARDIO, jugador,
            "El jugador declaró un comprobante después de vencer la retención; requiere conciliación manual.",
            {"referencia": pago.referencia},
        )
        _actualizar_auditoria(jugador, "declarar_pago_tardio", pago)
        return pago, True
    if pago.estado == EstadoPagoReserva.VENCIDO:
        raise ValidationError({"estado": "El pago ya venció; genera una nueva solicitud si el horario sigue retenido."})
    if not reserva.revision_pago_extendida:
        minutos = settings.RESERVA_REVISION_PAGO_MINUTOS
        reserva.revision_pago_vence_en = ahora + timedelta(minutes=minutos)
        reserva.revision_pago_extendida = True
        reserva.save(update_fields=["revision_pago_vence_en", "revision_pago_extendida", "actualizada_en"])
        programar_cambio_intervalo(
            reserva.cancha_id, reserva.inicio, reserva.fin, "retencion_pago_extendida",
        )
    pago.referencia = referencia.strip()
    pago.observacion_jugador = observacion.strip()
    pago.declarado_en = ahora
    _registrar_estado(
        pago, EstadoPagoReserva.PENDIENTE_REVISION, jugador,
        "El jugador declaró que adjuntó el comprobante por WhatsApp; no equivale a verificación.",
        {"referencia": pago.referencia},
    )
    cambiar_estado(reserva, EstadoReserva.PENDIENTE_VERIFICACION, "El jugador declaró un comprobante pendiente de verificación.", jugador)
    _actualizar_auditoria(jugador, "declarar_comprobante_pago", pago)
    return pago, False


def pago_administrable(usuario, pago_id: int) -> PagoReserva:
    pago = get_object_or_404(
        PagoReserva.objects.filter(reserva__cancha__in=canchas_visibles(usuario))
        .exclude(reserva__jugador=usuario).select_related(
            "reserva", "reserva__cancha", "reserva__cancha__sede", "reserva__cancha__sede__empresa",
            "reserva__jugador", "metodo",
        ), pk=pago_id,
    )
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=pago.reserva.cancha.sede.empresa,
            accion="consultar_pago_reserva_global", recurso="pago_reserva",
            recurso_id=pago.pk, datos={"codigo_reserva": pago.reserva.codigo},
        )
    return pago


def listar_pagos_administrables(usuario, filtros: dict) -> list[PagoReserva]:
    queryset = PagoReserva.objects.filter(
        reserva__cancha__in=canchas_visibles(usuario),
    ).exclude(reserva__jugador=usuario).select_related(
        "reserva", "reserva__cancha", "reserva__cancha__sede", "reserva__cancha__sede__empresa",
        "reserva__jugador", "metodo",
    ).prefetch_related("historial__actor")
    if filtros.get("sede"):
        queryset = queryset.filter(reserva__cancha__sede_id=filtros["sede"])
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("desde"):
        queryset = queryset.filter(reserva__inicio__date__gte=filtros["desde"])
    if filtros.get("hasta"):
        queryset = queryset.filter(reserva__inicio__date__lte=filtros["hasta"])
    termino = filtros.get("q", "").strip()
    if termino:
        queryset = queryset.filter(
            Q(reserva__codigo__icontains=termino)
            | Q(reserva__jugador__username__icontains=termino)
            | Q(reserva__jugador__email__icontains=termino)
        )
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, accion="consultar_pagos_reserva_globales", recurso="pagos_reserva",
            datos={"sede": filtros.get("sede"), "estado": filtros.get("estado")},
        )
    return list(queryset.order_by("-creado_en", "-id")[:100])


def _pago_bloqueado(pago_id: int) -> PagoReserva:
    pago = PagoReserva.objects.only("pk", "reserva_id").get(pk=pago_id)
    reserva = Reserva.objects.only("pk", "cancha_id").get(pk=pago.reserva_id)
    Cancha.objects.select_for_update().get(pk=reserva.cancha_id)
    Reserva.objects.select_for_update().get(pk=reserva.pk)
    return PagoReserva.objects.select_for_update().select_related(
        "reserva", "reserva__cancha", "reserva__cancha__sede", "reserva__cancha__sede__empresa", "metodo",
    ).get(pk=pago.pk)


def _vencer_pago_si_corresponde(pago: PagoReserva, ahora) -> bool:
    reserva = pago.reserva
    if reserva.estado in ESTADOS_CON_PLAZO and fecha_limite(reserva) <= ahora:
        _vencer_de_cancha(reserva.cancha_id, ahora)
        pago.refresh_from_db()
        return True
    return False


@transaction.atomic
def aprobar_pago(usuario, pago_id: int, importe: Decimal | None, motivo: str = "") -> tuple[PagoReserva, bool]:
    pago = _pago_bloqueado(pago_id)
    if pago.estado == EstadoPagoReserva.APROBADO:
        return pago, True
    if pago.estado != EstadoPagoReserva.PENDIENTE_REVISION:
        raise ValidationError({"estado": "Solo puedes aprobar un comprobante pendiente de revisión."})
    ahora = timezone.now()
    if _vencer_pago_si_corresponde(pago, ahora):
        return pago, False
    reserva = pago.reserva
    pagado = importe_pagado(reserva)
    pendiente = reserva.importe_total - pagado
    verificado = importe if importe is not None else pago.importe_solicitado
    if verificado < pago.importe_solicitado:
        raise ValidationError({"importe_verificado": "El importe no alcanza el monto solicitado."})
    if verificado > pendiente:
        raise ValidationError({"importe_verificado": "El importe supera el saldo de la reserva."})
    if pagado + verificado < reserva.adelanto_minimo:
        raise ValidationError({"importe_verificado": "El pago acumulado no alcanza el adelanto mínimo."})
    pago.importe_verificado = verificado
    pago.revisado_en = ahora
    pago.revisor = usuario
    pago.motivo_revision = motivo.strip()
    _registrar_estado(
        pago, EstadoPagoReserva.APROBADO, usuario,
        motivo.strip() or "El empleado verificó manualmente el pago recibido.",
        {"importe_verificado": str(verificado)},
    )
    cambiar_estado(
        reserva, EstadoReserva.PENDIENTE_CONFIRMACION,
        "Pago verificado; confirmación, correo y QR corresponden a la Fase 4D.", usuario,
    )
    _actualizar_auditoria(usuario, "aprobar_pago_reserva", pago, {"importe_verificado": str(verificado)})
    return pago, True


@transaction.atomic
def rechazar_pago(usuario, pago_id: int, motivo: str) -> tuple[PagoReserva, bool]:
    pago = _pago_bloqueado(pago_id)
    if pago.estado == EstadoPagoReserva.RECHAZADO:
        return pago, True
    if pago.estado != EstadoPagoReserva.PENDIENTE_REVISION:
        raise ValidationError({"estado": "Solo puedes rechazar un comprobante pendiente de revisión."})
    ahora = timezone.now()
    if _vencer_pago_si_corresponde(pago, ahora):
        return pago, False
    reserva = pago.reserva
    pago.revisor = usuario
    pago.revisado_en = ahora
    pago.motivo_revision = motivo.strip()
    _registrar_estado(pago, EstadoPagoReserva.RECHAZADO, usuario, motivo.strip())
    cambiar_estado(
        reserva, EstadoReserva.PENDIENTE_PAGO,
        "El empleado rechazó el comprobante; la reserva conserva el vencimiento original.", usuario,
    )
    _actualizar_auditoria(usuario, "rechazar_pago_reserva", pago, {"motivo": motivo.strip()})
    return pago, True


def cerrar_pagos_vencidos(reserva: Reserva, ahora) -> None:
    pendientes = PagoReserva.objects.select_for_update().filter(
        reserva=reserva, estado__in=PAGOS_ACTIVOS,
    )
    for pago in pendientes:
        _registrar_estado(
            pago, EstadoPagoReserva.VENCIDO, None,
            "Venció la retención mientras el pago esperaba envío o revisión.",
        )
    aprobados = PagoReserva.objects.select_for_update().filter(
        reserva=reserva, estado=EstadoPagoReserva.APROBADO, requiere_conciliacion=False,
    )
    for pago in aprobados:
        pago.requiere_conciliacion = True
        pago.save(update_fields=["requiere_conciliacion"])
        HistorialPagoReserva.objects.create(
            pago=pago, estado_anterior=pago.estado, estado_nuevo=pago.estado,
            motivo="La reserva venció después de recibir un pago; requiere conciliación manual.",
            actor=None, datos={"fecha_vencimiento": ahora.isoformat()},
        )
