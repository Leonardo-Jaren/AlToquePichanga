from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha, EstadoCancha
from apps.empresas.models import Empresa, EstadoEmpresa, MembresiaEmpresa, RolEmpresa
from apps.horarios.models import HorarioSede, IntervaloHorarioSede
from apps.reservas.models import (
    BloqueReserva,
    EstadoReserva,
    Reserva,
)
from apps.reservas.services.reservas import HorarioNoDisponible, crear_retencion
from apps.reservas.services.retenciones import vencer_retenciones_vencidas
from apps.sedes.models import AsignacionSede, Sede
from apps.tarifas.models import ReglaTarifa, TipoTarifa

ZONA = ZoneInfo("America/Lima")


def _proximo_dia(dia: int) -> date:
    hoy = timezone.localdate()
    diferencia = (dia - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=diferencia)


def _contexto(correo: str, *, dia: date | None = None, apertura="18:00", cierre="23:00"):
    dia = dia or _proximo_dia(0)
    usuario = User.objects.create_user(username=correo, email=correo, password="AlToque-Local-493!")
    empresa = Empresa.objects.create(nombre=f"Empresa {correo}", estado=EstadoEmpresa.ACTIVA)
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=empresa, rol=RolEmpresa.DUENO)
    sede = Sede.objects.create(empresa=empresa, nombre="Sede Central", direccion="Av. Lima 100")
    cancha = Cancha.objects.create(
        sede=sede, nombre="Cancha 1", modalidad=7, tipo_superficie="Sintético",
        publicada=True,
    )
    horario = HorarioSede.objects.create(sede=sede, configurado=True)
    IntervaloHorarioSede.objects.create(
        horario=horario, dia_semana=dia.weekday(),
        hora_apertura=time.fromisoformat(apertura), hora_cierre=time.fromisoformat(cierre),
    )
    ReglaTarifa.objects.create(
        cancha=cancha, tipo=TipoTarifa.NOCTURNA, nombre="Base de prueba",
        dias_semana=[dia.weekday()], hora_inicio=time(18), hora_fin=time(23),
        vigente_desde=timezone.localdate(), precio_hora=Decimal("50.00"),
        moneda="PEN", creado_por=usuario,
    )
    return usuario, empresa, sede, cancha, dia


def _solicitar(api: APIClient, cancha: Cancha, dia: date, hora="18:00", duracion=1, clave=None):
    return api.post("/api/reservas/", {
        "cancha_id": cancha.pk,
        "fecha": dia.isoformat(),
        "hora_inicio": hora,
        "duracion_horas": duracion,
        "clave_idempotencia": str(clave or uuid4()),
    }, format="json")


@pytest.mark.django_db
def test_crea_reserva_una_hora_con_total_adelanto_e_historial():
    jugador = User.objects.create_user(username="jugador-a@example.test", email="jugador-a@example.test")
    _, _, _, cancha, dia = _contexto("dueno-a@example.test")
    api = APIClient()
    api.force_authenticate(jugador)

    respuesta = _solicitar(api, cancha, dia)

    assert respuesta.status_code == 201, respuesta.data
    assert respuesta.data["estado"] == EstadoReserva.RETENIDA
    assert respuesta.data["importe_total"] == "50.00"
    assert respuesta.data["adelanto_minimo"] == "25.00"
    assert len(respuesta.data["cotizacion_aplicada"]["bloques"]) == 1
    reserva = Reserva.objects.get(codigo=respuesta.data["codigo"])
    assert reserva.bloques.count() == 1
    assert list(reserva.historial_estados.values_list("estado_nuevo", flat=True)) == ["retenida"]


@pytest.mark.django_db
def test_crea_varias_horas_y_cotiza_tarifa_especial_historica():
    jugador = User.objects.create_user(username="jugador-b@example.test", email="jugador-b@example.test")
    _, _, _, cancha, dia = _contexto("dueno-b@example.test")
    ReglaTarifa.objects.create(
        cancha=cancha, tipo=TipoTarifa.ESPECIAL, nombre="Fecha de prueba",
        fecha_aplicable_desde=dia, fecha_aplicable_hasta=dia,
        hora_inicio=time(18), hora_fin=time(23), vigente_desde=dia,
        precio_hora=Decimal("80.00"), moneda="PEN", creado_por=jugador,
    )
    api = APIClient()
    api.force_authenticate(jugador)

    respuesta = _solicitar(api, cancha, dia, duracion=2)

    assert respuesta.status_code == 201, respuesta.data
    assert respuesta.data["importe_total"] == "160.00"
    assert respuesta.data["adelanto_minimo"] == "80.00"
    assert len(respuesta.data["cotizacion_aplicada"]["bloques"]) == 2
    ReglaTarifa.objects.filter(cancha=cancha, tipo=TipoTarifa.ESPECIAL).update(activa=False)
    assert Reserva.objects.get(codigo=respuesta.data["codigo"]).cotizacion_aplicada["total"] == "160.00"


@pytest.mark.django_db
def test_conflicto_parcial_y_reintento_idempotente():
    jugador_a = User.objects.create_user(username="jugador-c@example.test", email="jugador-c@example.test")
    jugador_b = User.objects.create_user(username="jugador-d@example.test", email="jugador-d@example.test")
    _, _, _, cancha, dia = _contexto("dueno-c@example.test")
    clave = uuid4()
    api_a = APIClient()
    api_a.force_authenticate(jugador_a)
    api_b = APIClient()
    api_b.force_authenticate(jugador_b)

    primera = _solicitar(api_a, cancha, dia, hora="19:00", duracion=2, clave=clave)
    reintento = _solicitar(api_a, cancha, dia, hora="19:00", duracion=2, clave=clave)
    clave_reutilizada = _solicitar(api_a, cancha, dia, hora="18:00", duracion=2, clave=clave)
    superpuesta = _solicitar(api_b, cancha, dia, hora="20:00", duracion=2)

    assert primera.status_code == 201, primera.data
    assert reintento.status_code == 200, reintento.data
    assert reintento.data["codigo"] == primera.data["codigo"]
    assert clave_reutilizada.status_code == 400
    assert superpuesta.status_code == 409, superpuesta.data
    assert BloqueReserva.objects.filter(reserva__estado=EstadoReserva.RETENIDA).count() == 2

    reserva = Reserva.objects.get(codigo=primera.data["codigo"])
    inicio = reserva.inicio + timedelta(minutes=30)
    with pytest.raises(IntegrityError), transaction.atomic():
        BloqueReserva.objects.create(
            reserva=reserva, cancha=cancha, inicio=inicio, fin=inicio + timedelta(hours=1),
        )


@pytest.mark.django_db
def test_disponibilidad_publica_refleja_retencion_sin_datos_personales():
    jugador = User.objects.create_user(username="jugador-e@example.test", email="jugador-e@example.test")
    _, _, _, cancha, dia = _contexto("dueno-e@example.test")
    api = APIClient()
    api.force_authenticate(jugador)
    reserva = _solicitar(api, cancha, dia)
    consulta = APIClient().get(
        f"/api/publico/canchas/{cancha.pk}/disponibilidad/",
        {"desde": dia.isoformat(), "hasta": dia.isoformat()},
    )
    cotizacion_ocupada = APIClient().post(
        f"/api/publico/canchas/{cancha.pk}/cotizar/",
        {"fecha": dia.isoformat(), "hora_inicio": "18:00", "duracion_horas": 1},
        format="json",
    )

    assert reserva.status_code == 201
    assert consulta.status_code == 200
    assert consulta.data["considera_reservas"] is True
    assert cotizacion_ocupada.status_code == 409
    bloque = next(item for item in consulta.data["bloques"] if item["estado_reserva"])
    assert bloque["reservable"] is False
    assert bloque["estado"] == "retenida"
    assert "jugador" not in bloque and "correo" not in bloque and "importe" not in bloque


@pytest.mark.django_db
def test_cancelacion_y_vencimiento_liberan_bloques_y_dejan_historial():
    jugador = User.objects.create_user(username="jugador-f@example.test", email="jugador-f@example.test")
    _, _, _, cancha, dia = _contexto("dueno-f@example.test")
    api = APIClient()
    api.force_authenticate(jugador)
    creada = _solicitar(api, cancha, dia)
    codigo = creada.data["codigo"]
    cancelada = api.post(f"/api/reservas/{codigo}/cancelar/", {}, format="json")
    assert cancelada.status_code == 200
    assert cancelada.data["estado"] == EstadoReserva.CANCELADA
    assert Reserva.objects.get(codigo=codigo).bloques.get().liberado_en is not None

    segunda = _solicitar(api, cancha, dia, clave=uuid4())
    assert segunda.status_code == 201, segunda.data
    Reserva.objects.filter(codigo=segunda.data["codigo"]).update(
        retencion_vence_en=timezone.now() - timedelta(seconds=1)
    )
    assert vencer_retenciones_vencidas() == 1
    vencida = Reserva.objects.get(codigo=segunda.data["codigo"])
    assert vencida.estado == EstadoReserva.VENCIDA
    assert vencida.bloques.get().liberado_en is not None
    assert vencida.historial_estados.count() == 2


@pytest.mark.django_db
def test_jugadores_y_personal_no_cruzan_empresas():
    jugador_a = User.objects.create_user(username="jugador-g@example.test", email="jugador-g@example.test")
    jugador_b = User.objects.create_user(username="jugador-h@example.test", email="jugador-h@example.test")
    dueño_a, _, _, cancha_a, dia = _contexto("dueno-g@example.test")
    dueño_b, _, _, cancha_b, _ = _contexto("dueno-h@example.test", dia=dia)
    api_jugador = APIClient()
    api_jugador.force_authenticate(jugador_a)
    propia = _solicitar(api_jugador, cancha_a, dia)
    api_jugador_b = APIClient()
    api_jugador_b.force_authenticate(jugador_b)
    reserva_ajena = _solicitar(api_jugador_b, cancha_a, dia, hora="20:00")
    ajena = api_jugador.get(f"/api/reservas/{reserva_ajena.data['codigo']}/")
    cancelar_ajena = api_jugador.post(
        f"/api/reservas/{reserva_ajena.data['codigo']}/cancelar/", {}, format="json"
    )
    api_a = APIClient()
    api_a.force_authenticate(dueño_a)
    api_b = APIClient()
    api_b.force_authenticate(dueño_b)
    reserva_b = _solicitar(api_b, cancha_b, dia)
    lista_a = api_a.get("/api/reservas/administracion/")
    cruce_detalle = api_a.get(f"/api/reservas/administracion/{reserva_b.data['codigo']}/")

    assert propia.status_code == 201
    assert ajena.status_code == 404
    assert cancelar_ajena.status_code == 404
    assert lista_a.status_code == 200
    assert all(item["cancha_id"] == cancha_a.pk for item in lista_a.data["results"])
    assert cruce_detalle.status_code == 404


@pytest.mark.django_db
def test_solicitud_exige_sesion_y_personal_asignado_consulta_su_alcance():
    jugador = User.objects.create_user(username="jugador-i@example.test", email="jugador-i@example.test")
    _, empresa_a, sede_a, cancha_a, dia = _contexto("dueno-ia@example.test")
    _, empresa_b, sede_b, _, _ = _contexto("dueno-ib@example.test", dia=dia)
    sin_sesion = _solicitar(APIClient(), cancha_a, dia)
    autenticada = APIClient()
    autenticada.force_authenticate(jugador)
    respuesta_autenticada = _solicitar(autenticada, cancha_a, dia)

    admin_a = User.objects.create_user(username="admin-reservas-a@example.test")
    membresia_a = MembresiaEmpresa.objects.create(
        usuario=admin_a, empresa=empresa_a, rol=RolEmpresa.ADMINISTRADOR_SEDE,
    )
    AsignacionSede.objects.create(membresia=membresia_a, sede=sede_a)
    admin_b = User.objects.create_user(username="admin-reservas-b@example.test")
    membresia_b = MembresiaEmpresa.objects.create(
        usuario=admin_b, empresa=empresa_b, rol=RolEmpresa.ADMINISTRADOR_SEDE,
    )
    AsignacionSede.objects.create(membresia=membresia_b, sede=sede_b)
    personal_a = APIClient()
    personal_a.force_authenticate(admin_a)
    personal_b = APIClient()
    personal_b.force_authenticate(admin_b)
    codigo = respuesta_autenticada.data["codigo"]

    assert sin_sesion.status_code == 401
    assert respuesta_autenticada.status_code == 201
    listado_a = personal_a.get("/api/reservas/administracion/")
    detalle_a = personal_a.get(f"/api/reservas/administracion/{codigo}/")
    listado_b = personal_b.get("/api/reservas/administracion/")
    ajena_b = personal_b.get(f"/api/reservas/administracion/{codigo}/")
    assert listado_a.status_code == 200 and listado_a.data["count"] == 1
    assert detalle_a.status_code == 200 and detalle_a.data["jugador"]["id"] == jugador.pk
    assert listado_b.status_code == 200 and listado_b.data["count"] == 0
    assert ajena_b.status_code == 404


@pytest.mark.django_db
def test_reserva_de_horas_consecutivas_cruza_medianoche_con_tarifa_historica():
    jugador = User.objects.create_user(username="jugador-medianoche@example.test")
    _, _, _, cancha, dia = _contexto(
        "dueno-medianoche@example.test", dia=_proximo_dia(4),
        apertura="22:00", cierre="02:00",
    )
    intervalo = IntervaloHorarioSede.objects.get(horario__sede=cancha.sede, dia_semana=dia.weekday())
    intervalo.hora_apertura = time(22)
    intervalo.hora_cierre = time(2)
    intervalo.save(update_fields=["hora_apertura", "hora_cierre"])
    regla = ReglaTarifa.objects.get(cancha=cancha, tipo=TipoTarifa.NOCTURNA)
    regla.hora_inicio = time(22)
    regla.hora_fin = time(2)
    regla.save(update_fields=["hora_inicio", "hora_fin"])
    api = APIClient()
    api.force_authenticate(jugador)

    respuesta = _solicitar(api, cancha, dia, hora="22:00", duracion=3)

    assert respuesta.status_code == 201, respuesta.data
    reserva = Reserva.objects.get(codigo=respuesta.data["codigo"])
    assert timezone.localtime(reserva.fin, ZONA).date() == dia + timedelta(days=1)
    assert timezone.localtime(reserva.fin, ZONA).time() == time(1)
    assert [bloque["precio"] for bloque in reserva.cotizacion_aplicada["bloques"]] == [
        "50.00", "50.00", "50.00",
    ]


@pytest.mark.django_db
def test_rechaza_cancha_inactiva_horario_cerrado_y_horario_pasado():
    jugador = User.objects.create_user(username="jugador-i@example.test", email="jugador-i@example.test")
    _, _, _, cancha, dia = _contexto("dueno-i@example.test")
    api = APIClient()
    api.force_authenticate(jugador)
    Cancha.objects.filter(pk=cancha.pk).update(estado=EstadoCancha.INACTIVA)
    inactiva = _solicitar(api, cancha, dia)
    assert inactiva.status_code == 400
    Cancha.objects.filter(pk=cancha.pk).update(estado=EstadoCancha.ACTIVA)
    cerrada = _solicitar(api, cancha, dia, hora="23:00")
    pasada = api.post("/api/reservas/", {
        "cancha_id": cancha.pk,
        "fecha": (timezone.localdate() - timedelta(days=1)).isoformat(),
        "hora_inicio": "18:00", "duracion_horas": 1,
        "clave_idempotencia": str(uuid4()),
    }, format="json")
    assert cerrada.status_code == 400
    assert pasada.status_code == 400


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="Requiere PostgreSQL real y bloqueos por fila.")
def test_dos_conexiones_postgresql_solo_obtienen_una_retencion_superpuesta():
    usuario_a, _, _, cancha, dia = _contexto("concurrencia-a@example.test")
    usuario_b = User.objects.create_user(username="concurrencia-b@example.test", email="concurrencia-b@example.test")
    barrera = Barrier(2)

    def reservar(usuario_id: int, hora: time):
        close_old_connections()
        try:
            usuario = User.objects.get(pk=usuario_id)
            barrera.wait(timeout=5)
            crear_retencion(usuario, cancha.pk, dia, hora, 2, uuid4())
            return "creada"
        except HorarioNoDisponible:
            return "ocupada"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(
            lambda datos: reservar(*datos),
            [(usuario_a.pk, time(19)), (usuario_b.pk, time(20))],
        ))

    assert sorted(resultados) == ["creada", "ocupada"]
    assert Reserva.objects.filter(cancha=cancha, estado=EstadoReserva.RETENIDA).count() == 1
