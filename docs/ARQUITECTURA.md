# Arquitectura del Sistema — AlToque Pichanga

## 1. Principios

- Django y PostgreSQL compartidos; aislamiento por empresa y sede en repositorios y servicios.
- Nunca se concede autorización por un empresa_id o sede_id recibido del navegador.
- Modelos, campos y tablas de negocio en español. Se conserva auth.User.
- Vistas delgadas, reglas y transacciones en servicios, consultas centralizadas.
- Ningún archivo mantenido .py, .vue, .js o .ts supera 400 líneas; frontend solo JavaScript.
- No se agregaron dependencias pesadas para Fase 2.

## 2. Stack instalado

Backend: Python 3.12, Django 6.1.2, DRF, PostgreSQL 17, pytest-django y Ruff.
Frontend: Vue 3 Composition API, Vite, JavaScript, Tailwind, Pinia, Vue Router,
Axios, Lucide y Vitest. Channels/ASGI y Redis quedan disponibles para fases posteriores.

## 3. Módulos implementados hasta Fase 3B

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

