# Arquitectura del Sistema — AlToque Pichanga

## 1. Principios

- Django y PostgreSQL compartidos; aislamiento por empresa y sede en repositorios y servicios.
- Nunca se concede autorización por un empresa_id o sede_id recibido del navegador.
- Modelos, campos y tablas de negocio en español. Se conserva auth.User.
- Vistas delgadas, reglas y transacciones en servicios, consultas centralizadas.
- Ningún archivo mantenido .py, .vue, .js o .ts supera 400 líneas; frontend solo JavaScript.
- No se agregaron dependencias pesadas para Fase 2.

## 2. Stack instalado

Backend: Python 3.12, Django 6.1.2, DRF, PostgreSQL 17, pytest-django, Ruff,
Channels/ASGI y Redis para comunicación en tiempo real.
Frontend: Vue 3 Composition API, Vite, JavaScript, Tailwind, Pinia, Vue Router,
Axios, Lucide, Vitest y Playwright para la E2E de dos sesiones.

## 3. Módulos implementados hasta Fase 4B

Backend:

- apps/empresas: Empresa, MembresiaEmpresa, InvitacionEmpleado, RegistroAuditoria,
  servicios de empresa y personal, repositorios y autorización por rol.
- apps/sedes: Sede, AsignacionSede, ImagenSede, validación de imágenes y servicios.
- apps/suscripciones: PlanSuscripcion, SuscripcionEmpresa, PeriodoSuscripcion,
  SolicitudSuscripcion, PagoSuscripcion, ConfiguracionSuscripcion y reglas de límites.
- shared/archivos: comprobación de firma PNG/JPEG/WebP y máximo técnico de 5 MiB.
- `apps/canchas` implementa `Cancha`, `ImagenCancha`, consultas por alcance, servicios
  transaccionales, validación de fotos y endpoints de administración.
- `apps/horarios` mantiene intervalos semanales normalizados, herencia por día,
  excepciones, cálculo operativo y filtros por sedes/canchas visibles. No depende de
  reservas ni de canales WebSocket.

Frontend:

- modules/empresas: servicios Axios, selector persistido de empresa, panel de datos,
  sedes, empleados y suscripción.
- modules/administracion: consola global, planes, solicitudes, reglas de vigencia,
  vista acotada de administrador de sede y vista básica de cajero.
- `modules/canchas` implementa listado, filtros, formularios, fotos y estados, reutilizando
  el cliente HTTP, controles compartidos y tokens existentes.
- `modules/horarios` integra editores semanales, cierres/excepciones y consulta operativa
  en los paneles empresariales, sede, cajero de solo lectura y plataforma.
- shared/styles/tokens.css es la fuente de colores y tipografías; los componentes
  administrativos usan variables semánticas en ambos temas.

## 4. Aislamiento y permisos

- Dueño: solo empresas con membresía activa dueno; administra sus sedes y personal.
- Administrador de sede: ve las sedes asignadas; puede modificar solo esas sedes.
- Cajero: lectura limitada de sus sedes y vista básica; no gestiona sedes ni personal.
- Canchas: dueños y administradores de sede asignados leen y escriben dentro de sus sedes;
  el cajero solo consulta las canchas de sedes autorizadas; el superadministrador autorizado
  tiene alcance global. Las mutaciones administrativas se auditan.
- Jugador: no obtiene acceso a módulos privados de empresa.
- Superadministrador: alcance global solo por is_superuser, con registro de accesos
  globales y auditoría de cambios.
- Las vistas de detalle filtran por objeto autorizado; un identificador ajeno no revela
  el contenido de la empresa o sede.
- El dueño conserva acceso a estado y solicitud de regularización si su empresa está
  pendiente, suspendida o sin vigencia. Crear o editar recursos operativos exige empresa
  aprobada y suscripción efectiva vigente.

## 5. Límites y concurrencia SaaS

La operación empresa_con_cupo bloquea la fila de Empresa y la suscripción vigente con
select_for_update dentro de una transacción. Después cuenta sedes activas, membresías
operativas e invitaciones no vencidas y compara el resultado con el plan. La invitación
pendiente consume cupo; al aceptar, la invitación propia se excluye para no contarla dos
veces. En PostgreSQL se probaron solicitudes paralelas para límites de sedes y empleados.

Para Fase 3A, el límite de canchas se cuenta sobre todas las sedes de la empresa con bloqueo
transaccional en altas y reactivaciones. La política provisional cuenta `activa` y
`mantenimiento`; `inactiva` libera cupo. El supuesto queda pendiente de aprobación comercial
en DECISIONES.md. El superadministrador usa su
acceso global autorizado y las acciones globales quedan auditadas.

El precio viaja y se almacena como Decimal/DecimalField. El frontend mantiene los importes
como texto decimal y los agrupa sin convertirlos a Number. Una solicitud conserva el precio
y periodicidad presentados; cada aprobación crea un PeriodoSuscripcion con copia del plan,
importe, moneda y fechas. El pago SaaS se relaciona con su solicitud, separado de reservas.

La plataforma revisa manualmente las solicitudes. El enlace de invitación usa token aleatorio;
la base guarda SHA-256, vencimiento y estados de aceptación/cancelación. El correo queda
encolado en CorreoPendiente y nunca se devuelve el token desde la API de listado.

## 6. Endpoints de Fase 2

Empresas:

- POST /api/empresas/ registra una empresa pendiente.
- GET /api/empresas/administradas/ lista empresas propias con búsqueda y paginación.
- GET/PATCH /api/empresas/administradas/{id}/ consulta o modifica una empresa propia.
- GET /api/empresas/plataforma/ y GET/PATCH /api/empresas/plataforma/{id}/ son globales
  y exclusivos del superadministrador.

Personal:

- GET/POST /api/empresas/administradas/{id}/personal/
- POST /api/empresas/administradas/{id}/personal/{membresia}/revocar/
- POST /api/empresas/administradas/{id}/invitaciones/{invitacion}/revocar/
- POST /api/empresas/invitaciones/aceptar/
- Un registro público puede aceptar la invitación usando el token recibido por correo.

Sedes:

- GET/POST /api/sedes/, con GET/PATCH /api/sedes/{id}/.
- POST /api/sedes/{id}/estado/ con confirmación explícita.
- POST /api/sedes/{id}/imagenes/ y POST /api/sedes/{id}/imagenes/{imagen}/retirar/.

Suscripciones SaaS:

- GET /api/suscripciones/planes/ muestra planes disponibles.
- GET/POST /api/empresas/administradas/{id}/suscripcion/ consulta o solicita.
- GET/POST /api/plataforma/planes/ y PATCH /api/plataforma/planes/{id}/ gestionan planes.
- GET /api/plataforma/solicitudes/ y POST /api/plataforma/solicitudes/{id}/resolver/
  permiten revisión manual.
- POST /api/plataforma/empresas/{id}/suscripcion/estado/ cambia estado autorizado.
- GET/PUT /api/plataforma/suscripciones/configuracion/ consulta o configura gracia.

## 7. Endpoints implementados en Fase 3A

- GET /api/canchas/ lista las canchas dentro del alcance autorizado; admite filtros por
  sede, modalidad, estado y nombre, además de paginación.
- POST /api/canchas/ registra una cancha en una sede autorizada y valida el cupo total de
  la empresa.
- GET/PATCH /api/canchas/{id}/ consulta o edita una cancha dentro del alcance autorizado.
- POST /api/canchas/{id}/estado/ cambia a `activa`, `inactiva` o `mantenimiento`; reactivar
  comprueba el cupo en la misma operación transaccional.
- POST /api/canchas/{id}/imagenes/ agrega una foto; POST
  /api/canchas/{id}/imagenes/{imagen_id}/retirar/ la retira lógicamente.
- Las fotos admitidas son PNG/JPEG/WebP, verificadas por firma y extensión, hasta 5 MiB.
  No se borran físicamente ni la cancha ni sus fotos. Las mutaciones generan auditoría.

Los endpoints filtran objetos por alcance antes de consultar o mutar. El detalle global y
las mutaciones del superadministrador quedan registrados; las imágenes se retiran de forma
lógica y no se borran físicamente.

## 8. Endpoints de Fase 3B

- GET/PUT `/api/sedes/{sede_id}/horario-semanal/`: consulta o reemplaza intervalos
  semanales estructurados; la mutación requiere permiso de administración y suscripción
  efectiva, salvo el superadministrador autorizado.
- GET/PUT `/api/canchas/{cancha_id}/horario-semanal/`: horario propio, herencia completa o
  `dias_heredados` (0=lunes…6=domingo) e intervalos efectivos. Los días propios deben
  quedar dentro del horario de sede.
- GET/POST `/api/horarios/excepciones/`: lista por alcance/rango o registra un cierre o
  ampliación con fecha-hora ISO-8601 y offset explícito, motivo y responsable.
- POST `/api/horarios/excepciones/{id}/anular/`: requiere confirmación y conserva el
  registro, actor, fecha y auditoría.
- GET `/api/canchas/{cancha_id}/disponibilidad-operativa/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`:
  devuelve bloques completos de 60 minutos con estado, motivo, hora local e indicador
  `considera_reservas: false`. El máximo inclusivo se configura mediante
  `MAX_DIAS_CONSULTA_DISPONIBILIDAD` (valor técnico inicial 31).

Todos los endpoints requieren autenticación. Los dueños se limitan a sus empresas; los
administradores de sede, a sedes asignadas; los cajeros solo consultan; el superadmin tiene
acceso global auditado. Los jugadores no tienen endpoint de horarios públicos en 3B.
Las ampliaciones forman bloques operativos, pero un cierre que intersecta un bloque lo
marca como cerrado y no habilitado. El frontend no presenta estos bloques como reservables.

## 9. Migraciones y compatibilidad

Las migraciones de Fase 2 son aditivas: empresas 0002 y 0003, sedes 0001 y
suscripciones 0001 y 0002. Fase 3A añade canchas 0001 y Fase 3B añade horarios 0001.
Se mantiene activa en Empresa para compatibilidad con Fase 1, sincronizada con estado por
los servicios de transición. Las tablas nuevas usan nombres españoles explícitos.

`showmigrations` confirmó todas estas migraciones aplicadas en la base PostgreSQL local de
desarrollo. `makemigrations --check --dry-run` no detectó cambios faltantes. Pytest usa una
base temporal separada.

## 10. Decisiones propuestas

Los límites null se comportan como ilimitados en el código; la gracia comienza en cero días;
la invitación vence por defecto en siete días; las renovaciones empiezan después del periodo
contratado. Son valores técnicos centrales y configurables donde corresponde, no aprobaciones
comerciales definitivas. Ver DECISIONES.md.

El máximo de canchas se aplica al total de la empresa. Qué estados consumen cupo sigue
siendo un supuesto pendiente de aprobación, aunque el contrato actual usa `activa` y
`mantenimiento` como estados que consumen y `inactiva` como estado que libera.


## 11. Módulo de tarifas — Fase 3C

`apps/tarifas` separa modelos, repositorio, serializadores, validación, gestión, cálculo e
integración de disponibilidad. `ReglaTarifa` pertenece a una cancha y guarda tipo, ámbito
semanal o fechas aplicables, horario, vigencia, importe Decimal, moneda, activación y
responsable. Desactivar conserva el historial.

- GET/POST `/api/canchas/{cancha_id}/tarifas/`: consulta y crea reglas dentro del alcance
  autorizado de la persona autenticada.
- PATCH `/api/canchas/{cancha_id}/tarifas/{tarifa_id}/`: actualiza una regla de esa cancha.
- POST `/api/canchas/{cancha_id}/tarifas/{tarifa_id}/estado/`: activa o desactiva con
  confirmación explícita y valida conflictos al activar.
- POST `/api/canchas/{cancha_id}/calcular-precio/`: calcula de 1 a 24 bloques de una hora,
  comprobando primero el horario operativo.
- GET de disponibilidad 3B incorpora `precio`, `tipo_tarifa`, `moneda` y `tarifa_estado`
  para bloques habilitados; los cerrados nunca muestran precio y se conserva
  `considera_reservas: false`.

El cálculo y las reglas viven en servicios. El frontend tiene paneles bajo
`modules/tarifas/components/`, divididos en formularios, listados, paneles y precios, y el
control reutilizable `shared/components/controles/SelectControl.vue`.

## 12. Calendario integrado — Fase 3D

`modules/calendario/` reúne el selector de sede/cancha, el calendario diario/semanal, la
vista pública y los controles de bloques en subcarpetas `components/`, `views/` y `utils/`.
Los paneles de dueño, administrador de sede, cajero y superadministrador reutilizan el mismo
calendario. La API de disponibilidad 3B y el cálculo tarifario 3C siguen siendo la fuente
única para estados, precios y cotizaciones; el navegador no suma importes ni reserva bloques.

`Cancha.publicada` es un permiso de publicación explícito, apagado por defecto. El dueño,
administrador de sede o superadministrador puede cambiarlo mediante el PATCH administrativo
existente para la cancha; cajeros solo consultan. Endpoints públicos, deliberadamente
`AllowAny` y limitados a canchas publicadas en sedes/empresas activas:

La base `VistaPublica` desactiva autenticación de sesión en estas rutas porque entregan datos
publicables o una cotización calculada sin persistencia; así, una cookie de sesión preexistente
no fuerza un token CSRF en una consulta pública. El panel administrativo conserva su
autenticación y validación CSRF.

- GET `/api/publico/canchas/` y GET `/api/publico/canchas/{cancha_id}/`: únicamente datos
  definidos como públicos (cancha, fotos activas y distrito/provincia/departamento de sede).
- GET `/api/publico/canchas/{cancha_id}/disponibilidad/?desde=&hasta=`: reutiliza los bloques
  operativos y las reglas tarifarias; considera retenciones con `considera_reservas: true`, omite precios en
  intervalos cerrados y reemplaza motivos internos de cierres por mensajes genéricos.
- POST `/api/publico/canchas/{cancha_id}/cotizar/`: usa el mismo servicio de cálculo
  Decimal/PEN del panel autenticado. Solo devuelve una estimación y no persiste ni bloquea.

La página Vue está disponible en `/canchas-publicas`. Ninguna ruta pública expone dirección,
contactos, empleados, membresías, suscripciones o datos de gestión. La autorización
administrativa sigue resolviéndose en Django por identidad y sede; `empresa_id` del navegador
no concede acceso.

## 13. Motor de reservas y retenciones — Fase 4A

apps.reservas mantiene modelos, serializadores, vistas, servicios de disponibilidad y estados,
y el comando expirar_retenciones. La empresa y la sede se resuelven mediante la relación
Reserva → Cancha → Sede → Empresa; no se duplican esos identificadores en la reserva.
El servicio reutiliza horarios, cierres y tarifas existentes, vuelve a cotizar en el servidor
y guarda una copia histórica del importe por bloque.

Endpoints:

- POST /api/reservas/: requiere sesión y crea una retención idempotente de 1 a 24 bloques.
- GET /api/reservas/mias/, GET /api/reservas/{codigo}/ y POST
  /api/reservas/{codigo}/cancelar/: solo el jugador propietario puede consultar o cancelar
  una retención vigente.
- GET /api/reservas/administracion/ y GET
  /api/reservas/administracion/{codigo}/: paginación y filtros dentro de las canchas que
  canchas_visibles(usuario) autoriza; el cajero es de lectura y el superadministrador se
  audita.
- GET /api/reservas/administracion/disponibilidad/{cancha_id}/?desde=&hasta=: consulta para
  paneles con alcance administrativo.
- GET /api/publico/canchas/{cancha_id}/disponibilidad/?desde=&hasta=: incorpora retenciones
  activas y devuelve considera_reservas: true, estado_reserva y reservable sin datos personales.
  La disponibilidad operativa autenticada de 3B sigue indicando false.
- POST /api/publico/canchas/{cancha_id}/cotizar/ sigue siendo de solo lectura y responde
  conflicto si el intervalo ya se retuvo.

Solo están habilitadas las transiciones inicial → retenida, retenida → vencida y
retenida → cancelada. Las opciones para pagos, rechazo, confirmación y finalización están
modeladas, pero no se aceptan por la API en esta fase. Cada cambio guarda motivo y responsable
cuando aplica.

Para impedir choques, crear_retencion usa transaction.atomic() y bloquea la fila de Cancha;
luego persiste una fila por hora. PostgreSQL mantiene la garantía final con btree_gist y una
restricción de exclusión sobre cancha + tstzrange(inicio, fin, '[)') para bloques no liberados.
Los límites adyacentes son válidos; cualquier solapamiento parcial se rechaza. Una clave única
por jugador vuelve idempotentes los reintentos. Cancelación y vencimiento liberan bloques sin
borrarlos.

RESERVA_RETENCION_MINUTOS acepta un entero positivo y tiene un valor técnico provisional de
15 minutos; la duración comercial está pendiente. El comando python manage.py
expirar_retenciones debe programarse en el servidor (propuesta operativa: cada minuto) para
vencer solicitudes incluso sin jugadores conectados. Leer disponibilidad ignora retenciones
expiradas aunque la tarea todavía no haya actualizado su estado.

El frontend público integra modules/reservas/: solicitud, código, contador informativo y
/mis-reservas. El panel administrativo reusa la matriz de horarios de Stitch, con resumen,
estados, detalle y filtros adaptados a los tokens aprobados de AlToque; TablaBase.vue,
ModalBase.vue y BotonBase.vue son controles comunes reutilizables. Fase 4A no incorpora pagos,
WhatsApp, correos de reserva ni QR.

## 14. Disponibilidad en tiempo real — Fase 4B

ASGI enruta `ws/disponibilidad/` mediante Django Channels, `AuthMiddlewareStack` y
`OriginValidator` contra `CORS_ALLOWED_ORIGINS`. El socket usa la cookie de sesión existente;
no acepta tokens ni credenciales en la URL. Los parámetros `canchas`, `desde` y `hasta` solo
identifican lo solicitado: el consumer vuelve a comprobar publicación, sesión, membresía y
alcance por sede en el servidor. Se permiten hasta 24 canchas y siete fechas por conexión.
Usuarios anónimos solo pueden suscribirse a canchas publicadas. Un superadministrador que
consulta una cancha privada genera un registro `AccesoPlataforma`.

Cada socket se une a grupos por cancha/fecha y a un grupo general de esa cancha para cambios
semanales, de tarifa o de estado. Retenciones nuevas, canceladas y vencidas notifican las
fechas locales afectadas. Cambios de horarios, excepciones, tarifas, cancha o sede también
emiten avisos. El payload solo incluye `tipo`, `cancha_id`, `fecha` y `motivo`; el consumidor
rechaza mensajes enviados por el cliente y revalida sesión y alcance antes de cada aviso.
Todos los productores usan `transaction.on_commit()`; una reversión no anuncia cambios.

En desarrollo puede usarse `InMemoryChannelLayer` con `DEBUG=True` y un solo proceso ASGI.
En producción se debe configurar `USE_REDIS_CHANNEL_LAYER=True` y `REDIS_URL` en el entorno;
la configuración falla al arrancar con `DEBUG=False` sin Redis. No guardar la URL con
credenciales en Git. La URL se puede dejar vacía para usar `REDIS_HOST`/`REDIS_PORT`.

Ejecutar `python manage.py expirar_retenciones --continuo --intervalo 60` en un proceso
supervisado, tanto en desarrollo como en producción. Este reutiliza el servicio atómico de 4A,
libera bloques en PostgreSQL y emite avisos al confirmar. Mantener también el comando de una
sola ejecución `python manage.py expirar_retenciones` para operación manual. La duración
`RESERVA_RETENCION_MINUTOS=15` permanece configurable y pendiente de aprobación comercial.

El frontend mantiene una conexión por calendario, reintenta con backoff limitado, hace una
consulta REST al reconectar y permite actualización manual cuando el socket falla. La API REST
sigue siendo la fuente de disponibilidad y PostgreSQL conserva la protección contra choques.

## 15. Pagos manuales de reservas — Fase 4C

`apps.pagos` mantiene los modelos `MetodoPagoSede`, `PagoReserva` y `HistorialPagoReserva`.
El método pertenece a una sede; el pago se relaciona con la reserva y el método de esa misma
sede, de modo que empresa y sede se resuelven desde la reserva autorizada en el servidor.
Este flujo no reutiliza `PagoSuscripcion`, no procesa dinero del SaaS y no integra pasarelas.

El jugador consulta `/api/pagos/reservas/<codigo>/`, crea una solicitud de adelanto, total o
saldo, y declara que envió el comprobante. El backend calcula el importe desde la cotización
histórica de la reserva, usa `Decimal`, limita a una solicitud pendiente por reserva e impide
que la declaración apruebe el pago. `wa.me` solo lleva el texto prellenado; el jugador agrega
manualmente la captura.

Dueños y administradores de sede pueden mantener los medios autorizados de sus sedes. Cajeros
leen los medios activos y pueden revisar pagos solo dentro de sus asignaciones. El jugador ve
únicamente sus propias reservas y medios activos destinados al pago. Las consultas globales
del superadministrador quedan auditadas y la configuración de cuentas no se delega al rol
global. Repositorios y servicios validan el alcance; la API no confía en `empresa_id` o
`sede_id` del navegador.

La revisión manual se implementa en `/api/pagos/administracion/`: lista filtrada, detalle,
aprobación y rechazo con motivo e historial de actor/fecha. Rechazar o aprobar requiere una
transición permitida, alcance de sede, transacción y bloqueo; la aprobación no emite correo,
QR ni finaliza la reserva. Esta última transición se reserva para la Fase 4D.

`RESERVA_REVISION_PAGO_MINUTOS` define el límite provisional de revisión y el jugador solo
puede extender la retención una vez al declarar el comprobante. Un pago aprobado que alcance
su vencimiento sin completar la fase posterior conserva el registro contable, libera el
bloque y requiere conciliación manual. La duración y la habilitación en producción están
pendientes de aprobación comercial; `PAGOS_RESERVA_HABILITADOS` queda desactivado por defecto
cuando `DEBUG=False`.
