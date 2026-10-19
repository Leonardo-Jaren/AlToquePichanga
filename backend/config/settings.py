"""
Django settings for AlToque Pichanga backend.
Configuración modular orientada a SaaS multiempresa con PostgreSQL y WebSockets.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Seguridad básica y modo de ejecución
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Configura SECRET_KEY para producción.")
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# Aplicaciones instaladas
# daphne debe ser la primera aplicación para habilitar ASGI en desarrollo
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Paquetes de terceros
    "rest_framework",
    "corsheaders",
    "channels",
    # Módulos del proyecto
    "shared",
    "apps.usuarios",
    "apps.empresas",
    "apps.sedes",
    "apps.suscripciones",
    "apps.canchas",
    "apps.horarios",
]

# Middlewares
MIDDLEWARE = [
    "shared.middleware.RespuestaPrivadaMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Base de datos principal: PostgreSQL
DB_NAME = os.getenv("DB_NAME", "altoque_pichanga_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}

# Configuración de Channels / WebSockets
USE_REDIS = os.getenv("USE_REDIS_CHANNEL_LAYER", "False").lower() in ("true", "1", "yes")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

if USE_REDIS:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(REDIS_HOST, int(REDIS_PORT))],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# Validación de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internacionalización y zona horaria (Perú / Lima)
LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configuración CORS
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.usuarios.permissions.SesionConCSRF"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# Sesión de servidor; usar el mismo hostname en Vue/Django durante el desarrollo.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 43200
PASSWORD_RESET_TIMEOUT = 3600
AUTH_RATE_WINDOW = int(os.getenv("AUTH_RATE_WINDOW", "900"))
AUTH_LOGIN_LIMIT = int(os.getenv("AUTH_LOGIN_LIMIT", "10"))
AUTH_LOGIN_IP_LIMIT = int(os.getenv("AUTH_LOGIN_IP_LIMIT", "60"))
AUTH_PUBLIC_LIMIT = int(os.getenv("AUTH_PUBLIC_LIMIT", "20"))
INVITACION_DIAS_VIGENCIA = int(os.getenv("INVITACION_DIAS_VIGENCIA", "7"))
MAILERS = {"default": {
    "BACKEND": os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"),
    "OPTIONS": {
        "host": os.getenv("EMAIL_HOST", "localhost"),
        "port": int(os.getenv("EMAIL_PORT", "587")),
        "username": os.getenv("EMAIL_HOST_USER", ""),
        "password": os.getenv("EMAIL_HOST_PASSWORD", ""),
        "use_tls": os.getenv("EMAIL_USE_TLS", "True").lower() == "true",
        "timeout": 10,
    },
}}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@localhost")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
MAX_DIAS_CONSULTA_DISPONIBILIDAD = int(
    os.getenv("MAX_DIAS_CONSULTA_DISPONIBILIDAD", "31")
)
