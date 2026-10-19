from rest_framework import serializers

from apps.empresas.models import Empresa, EstadoEmpresa, MembresiaEmpresa, RolEmpresa
from shared.archivos import validar_imagen_segura


class EntradaEstricta(serializers.Serializer):
    def to_internal_value(self, data):
        desconocidos = set(data.keys()) - set(self.fields) if hasattr(data, "keys") else set()
        if desconocidos:
            raise serializers.ValidationError({
                campo: ["Este campo no está permitido."] for campo in desconocidos
            })
        return super().to_internal_value(data)


class EmpresaEntrada(EntradaEstricta):
    razon_social = serializers.CharField(max_length=180, required=False)
    nombre_comercial = serializers.CharField(max_length=160, required=False, allow_blank=True)
    ruc = serializers.CharField(max_length=11, required=False, allow_blank=True)
    descripcion = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    correo_contacto = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    telefono_contacto = serializers.CharField(max_length=32, required=False, allow_blank=True)
    direccion_administrativa = serializers.CharField(max_length=240, required=False, allow_blank=True)
    logotipo = serializers.FileField(required=False, allow_empty_file=False)

    def validate_ruc(self, value):
        if value and (len(value) != 11 or not value.isdigit()):
            raise serializers.ValidationError("El RUC debe tener 11 dígitos.")
        return value

    def validate_logotipo(self, value):
        validar_imagen_segura(value)
        return value

    def validate(self, datos):
        instancia = self.context.get("empresa")
        razon = datos.get("razon_social", getattr(instancia, "razon_social", ""))
        comercial = datos.get("nombre_comercial", getattr(instancia, "nombre_comercial", ""))
        if not razon and not comercial:
            raise serializers.ValidationError({
                "razon_social": "Ingresa la razón social o el nombre comercial."
            })
        ruc = datos.get("ruc", getattr(instancia, "ruc", ""))
        if ruc:
            consulta = Empresa.objects.filter(ruc=ruc)
            if instancia:
                consulta = consulta.exclude(pk=instancia.pk)
            if consulta.exists():
                raise serializers.ValidationError({"ruc": "Este RUC ya está registrado."})
        return datos


def datos_empresa(empresa: Empresa) -> dict:
    return {
        "id": empresa.pk, "nombre": empresa.nombre, "razon_social": empresa.razon_social,
        "nombre_comercial": empresa.nombre_comercial, "ruc": empresa.ruc,
        "descripcion": empresa.descripcion, "correo_contacto": empresa.correo_contacto,
        "telefono_contacto": empresa.telefono_contacto,
        "direccion_administrativa": empresa.direccion_administrativa,
        "logotipo_url": empresa.logotipo.url if empresa.logotipo else None,
        "estado": empresa.estado, "activa": empresa.activa,
        "creada_en": empresa.creada_en.isoformat(),
    }


def responsables_empresa(empresa: Empresa) -> list[dict]:
    return [
        {"id": m.usuario_id, "correo": getattr(m.usuario.perfil, "correo", "") or "",
         "nombre": m.usuario.get_full_name(), "rol": m.rol}
        for m in MembresiaEmpresa.objects.filter(
            empresa=empresa, rol=RolEmpresa.DUENO, activa=True
        ).select_related("usuario", "usuario__perfil").order_by("usuario_id")
    ]


ETIQUETAS_ESTADO = dict(EstadoEmpresa.choices)
