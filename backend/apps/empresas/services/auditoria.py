from django.contrib.auth.models import User

from apps.empresas.models import Empresa, RegistroAuditoria


def auditar(
    actor: User,
    accion: str,
    recurso: str,
    recurso_id: int | None = None,
    empresa: Empresa | None = None,
    datos: dict | None = None,
) -> RegistroAuditoria:
    return RegistroAuditoria.objects.create(
        actor=actor, empresa=empresa, accion=accion, recurso=recurso,
        recurso_id=recurso_id, datos=datos or {},
    )
