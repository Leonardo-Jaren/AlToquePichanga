from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections, connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha
from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa
from apps.pagos.models import (
    EstadoPagoReserva,
    MetodoPagoSede,
    PagoReserva,
    TipoMetodoPago,
)
from apps.reservas.models import BloqueReserva, EstadoReserva, Reserva
from apps.reservas.services.retenciones import vencer_retenciones_vencidas
from apps.sedes.models import AsignacionSede, Sede


@pytest.fixture(autouse=True)
def pagos_habilitados(settings):
    settings.PAGOS_RESERVA_HABILITADOS = True
    settings.RESERVA_REVISION_PAGO_MINUTOS = 15


def _contexto(etiqueta="a"):
    jugador = User.objects.create_user(
        username=f"jugador-{etiqueta}@example.test", email=f"jugador-{etiqueta}@example.test",
    )
    dueno = User.objects.create_user(
        username=f"dueno-{etiqueta}@example.test", email=f"dueno-{etiqueta}@example.test",
    )
    cajero = User.objects.create_user(
        username=f"cajero-{etiqueta}@example.test", email=f"cajero-{etiqueta}@example.test",
    )
    empresa = Empresa.objects.create(nombre=f"Empresa {etiqueta}")
    MembresiaEmpresa.objects.create(usuario=dueno, empresa=empresa, rol=RolEmpresa.DUENO)
    MembresiaEmpresa.objects.create(usuario=cajero, empresa=empresa, rol=RolEmpresa.CAJERO)
    sede = Sede.objects.create(
        empresa=empresa, nombre=f"Sede {etiqueta}", direccion="Dirección de prueba",
        whatsapp_contacto="+51 999 000 000",
    )
    AsignacionSede.objects.create(sede=sede, membresia=cajero.membresias.get())
    cancha = Cancha.objects.create(
        sede=sede, nombre=f"Cancha {etiqueta}", modalidad=7,
        tipo_superficie="Sintético", publicada=True,
    )
    ahora = timezone.now()
    inicio = ahora + timedelta(days=3)
    reserva = Reserva.objects.create(
        jugador=jugador, cancha=cancha, inicio=inicio, fin=inicio + timedelta(hours=1),
        duracion_horas=1, importe_total=Decimal("50.00"), adelanto_minimo=Decimal("25.00"),
        moneda="PEN", estado=EstadoReserva.RETENIDA,
        retencion_vence_en=ahora + timedelta(minutes=15),
        cotizacion_aplicada={"total": "50.00", "moneda": "PEN", "bloques": [{"precio": "50.00"}]},
        clave_idempotencia=uuid4(),
    )
    BloqueReserva.objects.create(
        reserva=reserva, cancha=cancha, inicio=inicio, fin=inicio + timedelta(hours=1),
    )
    metodo = MetodoPagoSede.objects.create(
        sede=sede, tipo=TipoMetodoPago.YAPE, titular="Titular ficticio",
        numero_cuenta="999000000", activo=True,
    )
    return {"jugador": jugador, "dueno": dueno, "cajero": cajero, "empresa": empresa,
            "sede": sede, "cancha": cancha, "reserva": reserva, "metodo": metodo}


def _api(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


def _solicitar_pago(contexto, api=None, tipo="adelanto", clave=None):
    api = api or _api(contexto["jugador"])
    return api.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/solicitudes/",
        {"tipo": tipo, "metodo_id": contexto["metodo"].pk,
         "clave_idempotencia": str(clave or uuid4())}, format="json",
    )


@pytest.mark.django_db
def test_jugador_ve_solo_su_pago_y_whatsapp_no_aprueba_automaticamente():
    contexto = _contexto()
    api_jugador = _api(contexto["jugador"])

    vista = api_jugador.get(f"/api/pagos/reservas/{contexto['reserva'].codigo}/")
    assert vista.status_code == 200
    assert vista.data["metodos"][0]["tipo"] == "yape"
    enlace = urlparse(vista.data["whatsapp_url"])
    assert enlace.netloc == "wa.me"
    texto = parse_qs(enlace.query)["text"][0]
    assert contexto["reserva"].codigo in texto
    assert "Adjuntaré la captura manualmente" in texto

    solicitud = _solicitar_pago(contexto, api_jugador)
    assert solicitud.status_code == 201, solicitud.data
    assert solicitud.data["importe_solicitado"] == Decimal("25.00")
    assert solicitud.data["estado"] == EstadoPagoReserva.PENDIENTE_PAGO
    assert contexto["reserva"].__class__.objects.get(pk=contexto["reserva"].pk).estado == EstadoReserva.PENDIENTE_PAGO
    assert not PagoReserva.objects.get(pk=solicitud.data["id"]).declarado_en
    vista_con_solicitud = api_jugador.get(f"/api/pagos/reservas/{contexto['reserva'].codigo}/")
    texto_solicitud = parse_qs(urlparse(vista_con_solicitud.data["whatsapp_url"]).query)["text"][0]
    assert "Monto a verificar: S/ 25.00" in texto_solicitud

    declarar = api_jugador.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/{solicitud.data['id']}/declarar/",
        {"referencia": "OP-TEST-123", "observacion": "Captura adjuntada en WhatsApp"}, format="json",
    )
    assert declarar.status_code == 200, declarar.data
    assert declarar.data["estado"] == EstadoPagoReserva.PENDIENTE_REVISION
    reserva = Reserva.objects.get(pk=contexto["reserva"].pk)
    assert reserva.estado == EstadoReserva.PENDIENTE_VERIFICACION
    assert reserva.revision_pago_extendida is True
    assert reserva.revision_pago_vence_en > reserva.retencion_vence_en
    assert PagoReserva.objects.get(pk=solicitud.data["id"]).estado != EstadoPagoReserva.APROBADO


@pytest.mark.django_db
def test_cajero_revisa_adelanto_y_saldo_sin_confirmar_la_reserva():
    contexto = _contexto("saldo")
    api_jugador = _api(contexto["jugador"])
    api_cajero = _api(contexto["cajero"])
    pago = _solicitar_pago(contexto, api_jugador).data
    ruta_declaracion = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/"
    assert api_jugador.post(ruta_declaracion, {"referencia": "A-1"}, format="json").status_code == 200

    cola = api_cajero.get("/api/pagos/administracion/", {"estado": "pendiente_revision", "sede": contexto["sede"].pk})
    assert cola.status_code == 200
    assert cola.data["count"] == 1
    assert cola.data["results"][0]["codigo_reserva"] == contexto["reserva"].codigo
    aprobado = api_cajero.post(
        f"/api/pagos/administracion/{pago['id']}/aprobar/",
        {"importe_verificado": "25.00"}, format="json",
    )
    assert aprobado.status_code == 200, aprobado.data
    reserva = Reserva.objects.get(pk=contexto["reserva"].pk)
    assert reserva.estado == EstadoReserva.PENDIENTE_CONFIRMACION
    assert reserva.estado != EstadoReserva.CONFIRMADA

    saldo = _solicitar_pago(contexto, api_jugador, "saldo")
    assert saldo.status_code == 201, saldo.data
    assert saldo.data["importe_solicitado"] == Decimal("25.00")
    ruta_saldo = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{saldo.data['id']}/declarar/"
    assert api_jugador.post(ruta_saldo, {"referencia": "A-2"}, format="json").status_code == 200
    segundo = api_cajero.post(
        f"/api/pagos/administracion/{saldo.data['id']}/aprobar/", {}, format="json",
    )
    assert segundo.status_code == 200, segundo.data
    reserva.refresh_from_db()
    assert reserva.estado == EstadoReserva.PENDIENTE_CONFIRMACION
    assert PagoReserva.objects.filter(reserva=reserva, estado=EstadoPagoReserva.APROBADO).count() == 2


@pytest.mark.django_db
def test_importe_excesivo_autoverificacion_y_acceso_cruzado_se_rechazan():
    contexto = _contexto("aislamiento")
    otro = _contexto("ajena")
    api_jugador = _api(contexto["jugador"])
    api_cajero = _api(contexto["cajero"])
    pago = _solicitar_pago(contexto, api_jugador).data
    ruta = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/"
    assert api_jugador.post(ruta, {}, format="json").status_code == 200

    ruta_admin = f"/api/pagos/administracion/{pago['id']}/aprobar/"
    excesivo = api_cajero.post(ruta_admin, {"importe_verificado": "100.00"}, format="json")
    assert excesivo.status_code == 400
    assert api_jugador.get(f"/api/pagos/reservas/{otro['reserva'].codigo}/").status_code == 404
    assert _api(otro["cajero"]).get(f"/api/pagos/administracion/{pago['id']}/").status_code == 404

    metodo = api_jugador.post(
        f"/api/pagos/sedes/{contexto['sede'].pk}/medios/",
        {"tipo": "plin", "titular": "Jugador", "numero_cuenta": "999111222"}, format="json",
    )
    assert metodo.status_code == 403


@pytest.mark.django_db
def test_comprobante_tardio_registra_incidente_y_no_recupera_horario():
    contexto = _contexto("tarde")
    api_jugador = _api(contexto["jugador"])
    pago = _solicitar_pago(contexto, api_jugador).data
    Reserva.objects.filter(pk=contexto["reserva"].pk).update(
        retencion_vence_en=timezone.now() - timedelta(seconds=1),
    )

    respuesta = api_jugador.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/",
        {"referencia": "TRANSFERENCIA-TARDIA"}, format="json",
    )
    assert respuesta.status_code == 409
    assert respuesta.data["estado"] == EstadoPagoReserva.PAGO_TARDIO
    reserva = Reserva.objects.get(pk=contexto["reserva"].pk)
    assert reserva.estado == EstadoReserva.VENCIDA
    assert reserva.bloques.get().liberado_en is not None
    assert reserva.estado != EstadoReserva.CONFIRMADA


@pytest.mark.django_db
def test_vencimiento_con_pago_aprobado_marca_conciliacion_y_no_borra_historial():
    contexto = _contexto("conciliar")
    jugador_api = _api(contexto["jugador"])
    caja_api = _api(contexto["cajero"])
    pago = _solicitar_pago(contexto, jugador_api).data
    jugador_api.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/",
        {}, format="json",
    )
    caja_api.post(f"/api/pagos/administracion/{pago['id']}/aprobar/", {}, format="json")
    reserva = Reserva.objects.get(pk=contexto["reserva"].pk)
    Reserva.objects.filter(pk=reserva.pk).update(
        revision_pago_vence_en=timezone.now() - timedelta(seconds=1),
    )

    assert vencer_retenciones_vencidas() == 1
    reserva.refresh_from_db()
    pago_modelo = PagoReserva.objects.get(pk=pago["id"])
    assert reserva.estado == EstadoReserva.VENCIDA
    assert pago_modelo.estado == EstadoPagoReserva.APROBADO
    assert pago_modelo.requiere_conciliacion is True
    assert pago_modelo.historial.count() >= 2


@pytest.mark.django_db(transaction=True)
def test_solicitudes_simultaneas_crean_un_solo_pago_pendiente():
    contexto = _contexto("concurrencia")
    barrera = Barrier(2)

    def solicitar(clave):
        close_old_connections()
        cliente = APIClient()
        cliente.force_authenticate(User.objects.get(pk=contexto["jugador"].pk))
        barrera.wait(timeout=5)
        try:
            respuesta = cliente.post(
                f"/api/pagos/reservas/{contexto['reserva'].codigo}/solicitudes/",
                {"tipo": "adelanto", "metodo_id": contexto["metodo"].pk,
                 "clave_idempotencia": str(clave)}, format="json",
            )
            return respuesta.status_code
        finally:
            close_old_connections()

    if connection.vendor != "postgresql":
        pytest.skip("La protección de concurrencia requiere PostgreSQL.")
    with ThreadPoolExecutor(max_workers=2) as grupo:
        codigos = list(grupo.map(solicitar, (uuid4(), uuid4())))
    assert sorted(codigos) == [201, 400]
    assert PagoReserva.objects.filter(reserva=contexto["reserva"], estado__in=[
        EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION,
    ]).count() == 1
