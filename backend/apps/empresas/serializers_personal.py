from rest_framework import serializers

from apps.empresas.models import RolEmpresa
from apps.empresas.serializers import EntradaEstricta


class PersonalEntrada(EntradaEstricta):
    correo = serializers.EmailField(max_length=254)
    rol = serializers.ChoiceField(choices=RolEmpresa.choices)
    sedes = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )

    def validate_correo(self, value):
        return value.strip().lower()
