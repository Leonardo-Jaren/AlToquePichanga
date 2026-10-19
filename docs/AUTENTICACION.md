# Autenticación y operación — Fase 1

## Estructura

- apps/usuarios: models, repositories, serializers, services, permissions, views,
  migrations y comandos operativos.
- apps/empresas: modelo mínimo, membresías, repositorios por alcance, servicios y vistas.
- frontend/src/modules/autenticacion: vistas, componentes, composable de formulario,
  cliente de cuenta y store de autenticación.
- frontend/src/router/proteccion.js: consulta de sesión y comprobación por rol.
- shared.middleware.RespuestaPrivadaMiddleware: no-store y referrer para API privada.

## Endpoints

Prefijo /api/auth/. Las mutaciones requieren token CSRF y cookies de sesión.
GET csrf/ entrega el token en memoria. La cookie de sesión y la de CSRF son HttpOnly.

| Método / ruta | Acceso / resultado |
|---|---|
| GET csrf/ | Público; token CSRF en respuesta no almacenable |
| POST registro/ | Público; correo, nombre, apellidos opcional, contrasena; 201 + sesión |
| POST login/ | Público; correo y contrasena; 200 + sesión rotada |
| POST logout/ | Sesión; 204, invalida sesión del servidor |
| GET perfil/ | Sesión; datos propios y membresías activas |
| PATCH perfil/ | Sesión; solo nombre y apellidos |
| POST recuperar/ | Público; correo; respuesta idéntica exista o no |
| POST restablecer/ | Público; uid, token, contrasena; invalida sesiones anteriores |
| POST verificar-correo/ | Público; uid y token de propósito separado |
| POST google/iniciar/ | Público para login; sesión para vincular:true |
| GET google/retorno/ | Callback con state y code, redirección fija al frontend |
| GET /api/empresas/ | Dueño: solo sus empresas; plataforma: todas y auditado |
| GET /api/empresas/ID/ | Alcance resuelto por identidad; 404 ante empresa ajena |
| GET /api/panel/ROL/ | Sesión y permiso real comprobado por el servicio |

Usuario anónimo: 401 en rutas privadas. Falta de rol: 403. CSRF inválido: 403.
Límite de intentos: 429 con Retry-After. No hay escrituras públicas de membresías.
Campos adicionales como rol, empresa_id o is_superuser se rechazan, no se ignoran.

## Matriz de acceso

| Actor | Perfil propio / jugador | Empresa completa | Panel sede/caja provisional | Plataforma |
|---|---|---|---|---|
| Jugador | Sí | No | No | No |
| Dueño | Sí | Solo empresas con rol dueno | Solo si tiene el rol adicional | No |
| Administrador de sede | Sí | No | Administrador de sede | No |
| Cajero | Sí | No | Cajero | No |
| Superadministrador | Sí | Todas, auditado | Requiere membresía para actuar como personal | Sí |

Los paneles de sede/caja son marcadores de acceso, sin operaciones ni datos de sede.
La asignación concreta de sedes será obligatoria antes de autorizar esas operaciones.
La API nunca usa un ID del navegador como prueba de autorización.

## Sesiones y navegador

Usar http://localhost:5173 junto con http://localhost:8000. No mezclar localhost
con 127.0.0.1: las cookies dependen del hostname. FRONTEND_URL y CORS deben coincidir.
Vue usa withCredentials y pide un token CSRF antes de cada mutación, incluyendo
después del login que lo rota. Solo el tema se guarda en localStorage.

Sesión de servidor de 12 horas, SameSite=Lax; Secure cuando DEBUG=False.
Producción necesita HTTPS y un despliegue del mismo sitio (por ejemplo subdominios).
Los valores de tiempo y límites son valores técnicos iniciales, configurables o
centralizados, revisables para despliegue; no fijan políticas de reservas.

Los contadores viven en PostgreSQL, por IP directa y correo con HMAC. Defaults:
10 intentos por correo / 60 por IP en 900 segundos; 20 por IP para registro,
recuperación, enlaces y Google. No se confía en X-Forwarded-For. Un proxy debe
normalizar REMOTE_ADDR; el comando de correos limpia contadores vencidos.

## Correo y recuperación

Configurar EMAIL_* y DEFAULT_FROM_EMAIL mediante variables de entorno; se mapean
a MAILERS de Django 6.1. Las peticiones encolan mensajes, no contactan SMTP.
Programar (desde backend y con su entorno activado):

    python manage.py enviar_correos --limite 50

Ejecutar cada minuto con el programador del sistema. El comando reserva mensajes
con select_for_update(skip_locked=True), evita colisiones entre workers, aplica
backoff de 5 minutos por intento y limita a cinco intentos. Tras entrega borra el
contenido con el enlace. Revisar filas sin enviado_en e intentos=5 para incidencias.
Entrega al menos una vez; no se promete exactamente una entrega SMTP.

Los enlaces duran una hora. Restablecer contraseña usa tokens de Django,
es de un solo uso e invalida sesiones previas. El enlace de verificación tiene
propósito separado y no se invalida por el login automático de registro.
Los secretos de enlace viajan en el fragmento URL del frontend, no en su query.
Un usuario solo Google debe volver a Google; no se le envía recuperación local.

## Google

Añadida google-auth[requests] para verificación oficial de firma, audiencia,
emisor y expiración; transporte con timeout de 10 segundos.
El código se intercambia solo en servidor. State, nonce y verificador PKCE
permanecen en sesión, tienen 10 minutos de vigencia y se consumen al regresar.
No se solicita acceso offline ni se almacenan access/refresh/ID tokens.

1. Crear cliente OAuth de aplicación web en Google Cloud.
2. Configurar consentimiento y usuarios de prueba según el estado del proyecto.
3. Registrar exactamente http://localhost:8000/api/auth/google/retorno/.
4. Configurar GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI.
5. Ajustar FRONTEND_URL y el callback para HTTPS en producción.
6. Verificar manualmente login y vinculación con una cuenta real cuando haya credenciales.

Identidad estable: sub de Google. Se exige email_verified=true. Nunca se vincula
una cuenta local por coincidencia de correo: primero se ingresa con contraseña,
luego se pulsa Vincular mi cuenta de Google desde el perfil. El correo de Google
debe coincidir con el perfil. Una identidad ya vinculada a otra cuenta se rechaza.
Los errores redirigen a un destino fijo sin tokens ni mensajes del proveedor.

Fuentes: [OpenID Connect de Google](https://developers.google.com/identity/openid-connect/openid-connect)
y [google-auth ID token](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html).

## Provisión administrativa

Crear superadministrador solo por proceso interno:

    python manage.py createsuperuser
    python manage.py sincronizar_perfiles

El segundo comando no concede roles ni eleva privilegios.
Para datos de prueba/provisión interna, las membresías se crean mediante ORM
controlado; no se implementó una interfaz de alta de empresas o personal.
No usar is_staff como sustituto de is_superuser.

## Pendientes de despliegue

Credenciales Google, SMTP, ejecución periódica del worker y prueba de entrega real.
Configurar logs del proxy para omitir parámetros OAuth code/state, y nunca registrar
cuerpos de autenticación o cookies. DEBUG=False y SECRET_KEY obligatoria en producción.
Revisar contadores, fallos de correo y acceso global. No se ejecutó CI remoto.

