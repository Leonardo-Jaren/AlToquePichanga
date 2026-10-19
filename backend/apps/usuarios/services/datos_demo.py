"""Creación idempotente de datos locales para probar roles y horarios."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from apps.canchas.models import Cancha
from apps.empresas.models import (
    Empresa,
    EstadoEmpresa,
    MembresiaEmpresa,
    RolEmpresa,
)
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.models import (
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)
from apps.usuarios.models import PerfilUsuario

MARCA = "[DEMO ALTOQUE]"
PREFIJO_ID = "ALTOQUE-DEMO-F3B"
CORREOS = {
    "superadmin": "demo-superadmin@example.test",
    "dueno_a": "demo-dueno-a@example.test",
    "dueno_b": "demo-dueno-b@example.test",
    "admin_a": "demo-admin-sede-a@example.test",
    "cajero_a": "demo-cajero-a@example.test",
    "jugador": "demo-jugador@example.test",
}

USUARIOS = {
    "superadmin": ("demo_altoque_superadmin", "Superadministrador de plataforma", True),
    "dueno_a": ("demo_altoque_dueno_a", "Dueño de empresa A", False),
    "dueno_b": ("demo_altoque_dueno_b", "Dueño de empresa B", False),
    "admin_a": ("demo_altoque_admin_sede_a", "Administrador de sede A", False),
    "cajero_a": ("demo_altoque_cajero_a", "Cajero de sede A", False),
    "jugador": ("demo_altoque_jugador", "Jugador sin membresía", False),
}

EMPRESAS = {
    "empresa_a": ("[DEMO ALTOQUE] Complejos Pichanga A", "empresa-a"),
    "empresa_b": ("[DEMO ALTOQUE] Complejos Pichanga B", "empresa-b"),
}

SEDES = {
    "sede_a_centro": ("empresa_a", "[DEMO ALTOQUE] Sede A Centro"),
    "sede_a_norte": ("empresa_a", "[DEMO ALTOQUE] Sede A Norte"),
    "sede_b_centro": ("empresa_b", "[DEMO ALTOQUE] Sede B Centro"),
    "sede_b_sur": ("empresa_b", "[DEMO ALTOQUE] Sede B Sur"),
}

CANCHAS = {
    "cancha_a_heredada": ("sede_a_centro", "[DEMO ALTOQUE] Cancha A heredada"),
    "cancha_a_propia": ("sede_a_centro", "[DEMO ALTOQUE] Cancha A con horario propio"),
    "cancha_a_norte": ("sede_a_norte", "[DEMO ALTOQUE] Cancha A Norte"),
    "cancha_b_centro_1": ("sede_b_centro", "[DEMO ALTOQUE] Cancha B Centro 1"),
    "cancha_b_centro_2": ("sede_b_centro", "[DEMO ALTOQUE] Cancha B Centro 2"),
    "cancha_b_sur": ("sede_b_sur", "[DEMO ALTOQUE] Cancha B Sur"),
}


def identidad_demo(clave: str) -> str:
    return f"{PREFIJO_ID}:{clave}"


def bloquear_ejecucion_concurrente() -> None:
    """Serializa dos ejecuciones para que no creen datos repetidos."""
    if connection.vendor != "postgresql":
        raise CommandError("Los datos demo solo se crean en PostgreSQL local.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [441021, 3])


def _marcado_unico(modelo, campo_marca: str, valor_marca: str):
    resultados = list(modelo.objects.filter(
        **{f"{campo_marca}__startswith": valor_marca}
    )[:2])
    if len(resultados) > 1:
        raise CommandError(f"Hay más de un registro demo con la marca {valor_marca}.")
    return resultados[0] if resultados else None


def _guardar_objeto_marcado(
    modelo,
    *,
    campo_marca: str,
    valor_marca: str,
    campo_nombre: str,
    nombre: str,
    valores: dict,
    relaciones_fijas: dict | None = None,
):
    objeto = _marcado_unico(modelo, campo_marca, valor_marca)
    if objeto is None:
        if modelo.objects.filter(**{campo_nombre: nombre}).exists():
            raise CommandError(f"Colisión con un registro no demo: {nombre}.")
        return modelo.objects.create(
            **{campo_marca: valor_marca, campo_nombre: nombre, **valores}
        )

    for campo, valor in (relaciones_fijas or {}).items():
        if getattr(objeto, campo) != valor:
            raise CommandError(f"El registro demo {valor_marca} tiene una relación inesperada.")
    for campo, valor in {campo_nombre: nombre, **valores}.items():
        setattr(objeto, campo, valor)
    objeto.save()
    return objeto


def _obtener_usuarios(credenciales: dict) -> dict[str, User]:
    usuarios: dict[str, User] = {}
    for clave, (username, apellido, es_superusuario) in USUARIOS.items():
        correo = CORREOS[clave]
        password = credenciales["usuarios"][clave]["contrasena"]
        encontrados = list(User.objects.filter(email__iexact=correo)[:2])
        por_nombre_usuario = User.objects.filter(username=username).first()
        if len(encontrados) > 1:
            raise CommandError(f"El correo {correo} está duplicado.")
        usuario = encontrados[0] if encontrados else por_nombre_usuario
        if usuario and (
            usuario.username != username
            or usuario.email.casefold() != correo.casefold()
            or not usuario.first_name.startswith(MARCA)
        ):
            raise CommandError(f"Colisión con una cuenta no demo: {correo}.")
        if usuario is None:
            usuario = User(username=username)

        usuario.email = correo
        usuario.first_name = f"{MARCA} {apellido}"
        usuario.last_name = "Usuario local de prueba"
        usuario.is_active = True
        usuario.is_superuser = es_superusuario
        usuario.is_staff = es_superusuario
        usuario.set_password(password)
        usuario.save()

        perfiles = list(PerfilUsuario.objects.filter(correo__iexact=correo)[:2])
        if any(perfil.usuario_id != usuario.pk for perfil in perfiles):
            raise CommandError(f"El correo de perfil {correo} ya pertenece a otra cuenta.")
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
        if perfil.correo and perfil.correo.casefold() != correo.casefold():
            raise CommandError(f"La cuenta demo {correo} tiene un perfil ajeno.")
        perfil.correo = correo
        perfil.correo_verificado = True
        perfil.save(update_fields=["correo", "correo_verificado"])
        usuarios[clave] = usuario
    return usuarios


def _obtener_empresas() -> dict[str, Empresa]:
    resultado = {}
    for clave, (nombre, marca_clave) in EMPRESAS.items():
        marca = identidad_demo(marca_clave)
        resultado[clave] = _guardar_objeto_marcado(
            Empresa,
            campo_marca="descripcion",
            valor_marca=f"{MARCA} {marca}",
            campo_nombre="nombre",
            nombre=nombre,
            valores={
                "descripcion": f"{MARCA} {marca} — Empresa ficticia para pruebas locales.",
                "razon_social": nombre,
                "nombre_comercial": nombre,
                "estado": EstadoEmpresa.ACTIVA,
                "activa": True,
            },
        )
    return resultado


def _obtener_plan_y_suscripciones(empresas: dict) -> PlanSuscripcion:
    nombre = f"{MARCA} Plan local ilimitado"
    marca = f"{MARCA} {identidad_demo('plan-local')}"
    plan = _guardar_objeto_marcado(
        PlanSuscripcion,
        campo_marca="descripcion",
        valor_marca=marca,
        campo_nombre="nombre",
        nombre=nombre,
        valores={
            "descripcion": f"{marca} — Suscripción ficticia para pruebas locales.",
            "precio": Decimal("0.00"),
            "moneda": "PEN",
            "frecuencia": FrecuenciaSuscripcion.MENSUAL,
            "maximo_sedes": None,
            "maximo_empleados": None,
            "maximo_canchas": None,
            "activo": True,
        },
    )
    hoy = timezone.localdate()
    for empresa in empresas.values():
        suscripcion = SuscripcionEmpresa.objects.filter(empresa=empresa).first()
        if suscripcion and suscripcion.plan_id != plan.pk:
            raise CommandError(
                f"La empresa demo {empresa.nombre} tiene una suscripción ajena; no se modificó."
            )
        if suscripcion is None:
            SuscripcionEmpresa.objects.create(
                empresa=empresa,
                plan=plan,
                estado=EstadoSuscripcion.ACTIVA,
                fecha_inicio=hoy,
                fecha_vencimiento=hoy + timedelta(days=365),
                importe_acordado=plan.precio,
                moneda_acordada=plan.moneda,
                frecuencia_acordada=plan.frecuencia,
            )
        else:
            suscripcion.estado = EstadoSuscripcion.ACTIVA
            suscripcion.fecha_inicio = hoy
            suscripcion.fecha_vencimiento = hoy + timedelta(days=365)
            suscripcion.importe_acordado = plan.precio
            suscripcion.moneda_acordada = plan.moneda
            suscripcion.frecuencia_acordada = plan.frecuencia
            suscripcion.save()
    return plan


def _obtener_sedes(empresas: dict) -> dict[str, Sede]:
    resultado = {}
    for clave, (empresa_clave, nombre) in SEDES.items():
        empresa = empresas[empresa_clave]
        marca = f"{MARCA} {identidad_demo(clave)}"
        resultado[clave] = _guardar_objeto_marcado(
            Sede,
            campo_marca="descripcion",
            valor_marca=marca,
            campo_nombre="nombre",
            nombre=nombre,
            relaciones_fijas={"empresa_id": empresa.pk},
            valores={
                "empresa": empresa,
                "descripcion": f"{marca} — Instalación ficticia para pruebas locales.",
                "direccion": "Dirección ficticia para pruebas locales",
                "departamento": "Huánuco",
                "provincia": "Huánuco",
                "distrito": "Huánuco",
                "activa": True,
            },
        )
    return resultado


def _obtener_canchas(sedes: dict) -> dict[str, Cancha]:
    resultado = {}
    for clave, (sede_clave, nombre) in CANCHAS.items():
        sede = sedes[sede_clave]
        marca = f"{MARCA} {identidad_demo(clave)}"
        resultado[clave] = _guardar_objeto_marcado(
            Cancha,
            campo_marca="descripcion",
            valor_marca=marca,
            campo_nombre="nombre",
            nombre=nombre,
            relaciones_fijas={"sede_id": sede.pk},
            valores={
                "sede": sede,
                "descripcion": f"{marca} — Cancha ficticia para pruebas locales.",
                "modalidad": 7,
                "tipo_superficie": "Sintético",
                "capacidad_jugadores": 14,
                "techada": False,
                "iluminacion": True,
                "caracteristicas": ["Datos de prueba"],
                "estado": "activa",
            },
        )
    return resultado


def _obtener_membresia(usuario: User, empresa: Empresa, rol: str) -> MembresiaEmpresa:
    ajenas = MembresiaEmpresa.objects.filter(
        usuario=usuario, empresa=empresa, activa=True
    ).exclude(rol=rol)
    if ajenas.exists():
        raise CommandError(f"La cuenta demo {usuario.email} tiene un rol inesperado.")
    membresia, _ = MembresiaEmpresa.objects.get_or_create(
        usuario=usuario, empresa=empresa, rol=rol,
        defaults={"activa": True},
    )
    if not membresia.activa:
        membresia.activa = True
        membresia.save(update_fields=["activa"])
    return membresia


def _asignar_sede(membresia: MembresiaEmpresa, sede: Sede) -> None:
    otras = AsignacionSede.objects.filter(membresia=membresia).exclude(sede=sede)
    if otras.exists():
        raise CommandError("La cuenta demo tiene asignaciones de sede inesperadas.")
    asignacion, _ = AsignacionSede.objects.get_or_create(
        membresia=membresia, sede=sede, defaults={"activa": True}
    )
    if not asignacion.activa:
        asignacion.activa = True
        asignacion.save(update_fields=["activa"])


def _validar_membresias_esperadas(usuarios: dict, empresas: dict) -> None:
    esperadas = {
        "superadmin": None,
        "dueno_a": (empresas["empresa_a"], RolEmpresa.DUENO),
        "dueno_b": (empresas["empresa_b"], RolEmpresa.DUENO),
        "admin_a": (empresas["empresa_a"], RolEmpresa.ADMINISTRADOR_SEDE),
        "cajero_a": (empresas["empresa_a"], RolEmpresa.CAJERO),
        "jugador": None,
    }
    for clave, esperado in esperadas.items():
        membresias = MembresiaEmpresa.objects.filter(usuario=usuarios[clave])
        if esperado is None:
            if membresias.exists():
                raise CommandError(f"La cuenta demo {usuarios[clave].email} debe carecer de membresías.")
            continue
        empresa, rol = esperado
        if membresias.exclude(empresa=empresa, rol=rol).exists():
            raise CommandError(
                f"La cuenta demo {usuarios[clave].email} tiene membresías ajenas al fixture."
            )


def crear_datos_demo(credenciales: dict) -> None:
    usuarios = _obtener_usuarios(credenciales)
    empresas = _obtener_empresas()
    _obtener_plan_y_suscripciones(empresas)
    sedes = _obtener_sedes(empresas)
    canchas = _obtener_canchas(sedes)
    from apps.usuarios.services.datos_demo_horarios import crear_horarios_demo

    crear_horarios_demo(sedes, canchas, usuarios)
    _validar_membresias_esperadas(usuarios, empresas)

    _obtener_membresia(usuarios["dueno_a"], empresas["empresa_a"], RolEmpresa.DUENO)
    _obtener_membresia(usuarios["dueno_b"], empresas["empresa_b"], RolEmpresa.DUENO)
    admin = _obtener_membresia(
        usuarios["admin_a"], empresas["empresa_a"], RolEmpresa.ADMINISTRADOR_SEDE
    )
    cajero = _obtener_membresia(
        usuarios["cajero_a"], empresas["empresa_a"], RolEmpresa.CAJERO
    )
    _asignar_sede(admin, sedes["sede_a_centro"])
    _asignar_sede(cajero, sedes["sede_a_centro"])
