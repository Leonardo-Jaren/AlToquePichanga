from pathlib import Path

from rest_framework.exceptions import ValidationError

MAXIMO_IMAGEN = 5 * 1024 * 1024
EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".webp"}


def validar_imagen_segura(archivo, extensiones_permitidas: set[str] | None = None) -> None:
    if archivo.size > MAXIMO_IMAGEN:
        raise ValidationError("La imagen no puede superar 5 MB.")
    extension = Path(getattr(archivo, "name", "")).suffix.lower()
    extensiones = extensiones_permitidas or EXTENSIONES_IMAGEN
    if extension not in extensiones:
        raise ValidationError("Usa una extensión PNG, JPG o WebP válida.")
    inicio = archivo.read(12)
    archivo.seek(0)
    es_png = inicio.startswith(b"\x89PNG\r\n\x1a\n")
    es_jpg = inicio.startswith(b"\xff\xd8\xff")
    es_webp = inicio.startswith(b"RIFF") and inicio[8:12] == b"WEBP"
    coincide = (
        (extension == ".png" and es_png)
        or (extension in {".jpg", ".jpeg"} and es_jpg)
        or (extension == ".webp" and es_webp)
    )
    if not coincide:
        raise ValidationError("Usa una imagen PNG, JPG o WebP válida.")
