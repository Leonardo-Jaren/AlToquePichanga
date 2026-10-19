from rest_framework import serializers


class EntradaEstricta(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"non_field_errors": ["Envía un objeto JSON válido."]})
        desconocidos = set(data) - set(self.fields)
        if desconocidos:
            raise serializers.ValidationError({
                campo: ["Este campo no está permitido."] for campo in desconocidos
            })
        return super().to_internal_value(data)


class CorreoEntrada(EntradaEstricta):
    correo = serializers.EmailField(max_length=254)

    def validate_correo(self, value: str) -> str:
        return value.strip().lower()


class PerfilEntrada(EntradaEstricta):
    nombre = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150, allow_blank=True, required=False)


class RegistroEntrada(CorreoEntrada, PerfilEntrada):
    contrasena = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    invitacion = serializers.CharField(max_length=100, required=False, write_only=True)


class LoginEntrada(CorreoEntrada):
    contrasena = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class TokenEntrada(EntradaEstricta):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=200)


class RestablecerEntrada(TokenEntrada):
    contrasena = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
