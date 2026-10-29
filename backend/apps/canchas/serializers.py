from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.canchas.models import Cancha, EstadoCancha, ImagenCancha
from apps.empresas.serializers import EntradaEstricta
from shared.archivos import EXTENSIONES_IMAGEN, validar_imagen_segura


class CanchaEntrada(EntradaEstricta):
    sede_id = serializers.IntegerField(min_value=1, required=False)
    nombre = serializers.CharField(max_length=160, required=False)
    descripcion = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    modalidad = serializers.IntegerField(min_value=1, max_value=32767, required=False)
    tipo_superficie = serializers.CharField(max_length=80, required=False)
    capacidad_jugadores = serializers.IntegerField(
        min_value=1, max_value=32767, required=False, allow_null=True
    )
    techada = serializers.BooleanField(required=False)
    iluminacion = serializers.BooleanField(required=False)
    publicada = serializers.BooleanField(required=False)
    caracteristicas = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        max_length=30,
        required=False,
    )
    imagen_principal = serializers.FileField(required=False, allow_empty_file=False)

    def validate_nombre(self, value: str) -> str:
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return nombre

    def validate_tipo_superficie(self, value: str) -> str:
        superficie = value.strip()
        if not superficie:
            raise serializers.ValidationError("Indica el tipo de superficie.")
        return superficie

    def validate_caracteristicas(self, value: list[str]) -> list[str]:
        resultado = [item.strip() for item in value]
        if any(not item for item in resultado):
            raise serializers.ValidationError("Cada característica debe tener texto.")
        return resultado

    def validate_imagen_principal(self, value: UploadedFile) -> UploadedFile:
        validar_imagen_segura(value, EXTENSIONES_IMAGEN)
        return value

    def validate(self, datos: dict) -> dict:
        cancha = self.context.get("cancha")
        if cancha and "sede_id" in datos:
            raise serializers.ValidationError({
                "sede_id": "Una cancha no se puede transferir de sede."
            })
        if not cancha:
            for campo in ("sede_id", "nombre", "modalidad", "tipo_superficie"):
                if campo not in datos:
                    raise serializers.ValidationError({campo: "Este campo es obligatorio."})
        return datos


class EstadoCanchaEntrada(EntradaEstricta):
    estado = serializers.ChoiceField(choices=EstadoCancha.choices)
    confirmar = serializers.BooleanField()


class ImagenCanchaEntrada(EntradaEstricta):
    archivo = serializers.FileField(required=True, allow_empty_file=False)
    descripcion = serializers.CharField(max_length=180, required=False, allow_blank=True)
    orden = serializers.IntegerField(min_value=0, required=False, default=0)
    principal = serializers.BooleanField(required=False, default=False)

    def validate_archivo(self, value: UploadedFile) -> UploadedFile:
        validar_imagen_segura(value, EXTENSIONES_IMAGEN)
        return value


def datos_imagen(
    imagen: ImagenCancha, cancha: Cancha | None = None
) -> dict[str, object]:
    principal = bool(cancha and cancha.imagen_principal.name == imagen.archivo.name)
    return {
        "id": imagen.pk,
        "url": imagen.archivo.url,
        "descripcion": imagen.descripcion,
        "orden": imagen.orden,
        "principal": principal,
    }


def datos_cancha(cancha: Cancha) -> dict[str, object]:
    imagenes = getattr(cancha, "imagenes_activas", None)
    if imagenes is None:
        imagenes = cancha.imagenes.filter(activa=True).order_by("orden", "id")
    return {
        "id": cancha.pk,
        "sede_id": cancha.sede_id,
        "sede": cancha.sede.nombre,
        "empresa_id": cancha.sede.empresa_id,
        "empresa": cancha.sede.empresa.nombre_visible,
        "nombre": cancha.nombre,
        "descripcion": cancha.descripcion,
        "modalidad": cancha.modalidad,
        "tipo_superficie": cancha.tipo_superficie,
        "capacidad_jugadores": cancha.capacidad_jugadores,
        "techada": cancha.techada,
        "iluminacion": cancha.iluminacion,
        "caracteristicas": cancha.caracteristicas,
        "estado": cancha.estado,
        "publicada": cancha.publicada,
        "imagen_principal_url": cancha.imagen_principal.url if cancha.imagen_principal else None,
        "imagenes": [datos_imagen(imagen, cancha) for imagen in imagenes],
        "creada_en": cancha.creada_en.isoformat(),
        "actualizada_en": cancha.actualizada_en.isoformat(),
    }
