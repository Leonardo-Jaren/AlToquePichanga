from decimal import Decimal

from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.sedes.models import ImagenSede, Sede
from shared.archivos import validar_imagen_segura

DIAS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"}


class SedeEntrada(EntradaEstricta):
    empresa_id = serializers.IntegerField(min_value=1, required=False)
    nombre = serializers.CharField(max_length=160, required=False)
    descripcion = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=240, required=False)
    departamento = serializers.CharField(max_length=100, required=False, allow_blank=True)
    provincia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    distrito = serializers.CharField(max_length=100, required=False, allow_blank=True)
    latitud = serializers.DecimalField(
        max_digits=8, decimal_places=6, min_value=Decimal("-90"),
        max_value=Decimal("90"), required=False, allow_null=True,
    )
    longitud = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-180"),
        max_value=Decimal("180"), required=False, allow_null=True,
    )
    telefono_contacto = serializers.CharField(max_length=32, required=False, allow_blank=True)
    whatsapp_contacto = serializers.CharField(max_length=32, required=False, allow_blank=True)
    correo_contacto = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    horario_general = serializers.JSONField(required=False)
    imagen_principal = serializers.FileField(required=False, allow_empty_file=False)

    def validate_horario_general(self, value):
        if not isinstance(value, dict) or set(value) - DIAS:
            raise serializers.ValidationError("Indica horarios con los días de la semana en español.")
        if any(not isinstance(texto, str) or len(texto) > 80 for texto in value.values()):
            raise serializers.ValidationError("Cada horario debe ser un texto breve.")
        return value

    def validate_imagen_principal(self, value):
        validar_imagen_segura(value)
        return value

    def validate(self, datos):
        sede = self.context.get("sede")
        if sede and "empresa_id" in datos:
            raise serializers.ValidationError({"empresa_id": "Una sede no se puede transferir de empresa."})
        if self.context.get("creando"):
            for campo in ("empresa_id", "nombre", "direccion"):
                if campo not in datos or not str(datos[campo]).strip():
                    raise serializers.ValidationError({campo: "Este campo es obligatorio."})
        latitud = datos.get("latitud", sede.latitud if sede else None)
        longitud = datos.get("longitud", sede.longitud if sede else None)
        if (latitud is None) != (longitud is None):
            raise serializers.ValidationError({
                "latitud": "Indica ambas coordenadas o deja las dos vacías."
            })
        return datos


class ImagenSedeEntrada(EntradaEstricta):
    archivo = serializers.FileField(required=True, allow_empty_file=False)
    descripcion = serializers.CharField(max_length=180, required=False, allow_blank=True)
    orden = serializers.IntegerField(min_value=0, required=False, default=0)

    def validate_archivo(self, value):
        validar_imagen_segura(value)
        return value


def datos_sede(sede: Sede, incluir_imagenes: bool = True) -> dict:
    datos = {
        "id": sede.pk, "empresa_id": sede.empresa_id, "empresa": sede.empresa.nombre_visible,
        "nombre": sede.nombre, "descripcion": sede.descripcion, "direccion": sede.direccion,
        "departamento": sede.departamento, "provincia": sede.provincia,
        "distrito": sede.distrito, "latitud": str(sede.latitud) if sede.latitud is not None else None,
        "longitud": str(sede.longitud) if sede.longitud is not None else None,
        "telefono_contacto": sede.telefono_contacto,
        "whatsapp_contacto": sede.whatsapp_contacto, "correo_contacto": sede.correo_contacto,
        "horario_general": sede.horario_general, "activa": sede.activa,
        "imagen_principal_url": sede.imagen_principal.url if sede.imagen_principal else None,
        "creada_en": sede.creada_en.isoformat(),
    }
    if incluir_imagenes:
        datos["imagenes"] = [{
            "id": imagen.pk, "url": imagen.archivo.url, "descripcion": imagen.descripcion,
            "orden": imagen.orden,
        } for imagen in sede.imagenes.filter(activa=True)]
    return datos


def datos_imagen(imagen: ImagenSede) -> dict:
    return {
        "id": imagen.pk, "url": imagen.archivo.url,
        "descripcion": imagen.descripcion, "orden": imagen.orden,
    }
