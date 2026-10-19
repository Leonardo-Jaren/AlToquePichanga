from django.db import migrations


def crear_perfiles(apps, schema_editor):
    Usuario = apps.get_model("auth", "User")
    Perfil = apps.get_model("usuarios", "PerfilUsuario")
    correos = set()
    for usuario in Usuario.objects.using(schema_editor.connection.alias).all().iterator():
        correo = usuario.email.strip().lower() or None
        if correo and correo in correos:
            raise RuntimeError("Existen correos duplicados. Resolverlos antes de migrar.")
        if correo:
            correos.add(correo)
        Perfil.objects.using(schema_editor.connection.alias).create(
            usuario_id=usuario.pk, correo=correo
        )


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0001_initial")]
    operations = [migrations.RunPython(crear_perfiles, migrations.RunPython.noop)]
