# Estado del Proyecto — AlToque Pichanga

Actualizado: 25 de octubre de 2026 (America/Lima).
Fases 2, 3A, 3B, 3C, 3D, 4A, 4B y 4C: **implementadas**. Los resultados de verificación están registrados en PLAN_PRUEBAS.md.
Siguiente fase: **Fase 4D — confirmación final, notificación y ticket QR**.

## Base conservada

- Backend Python 3.12.6, Django 6.1.2, Django REST Framework y PostgreSQL 17.
- Frontend Vue 3, JavaScript, Vite, Tailwind CSS, Pinia, Vue Router y Axios.
- Se conserva auth.User, AUTH_USER_MODEL y el historial de migraciones anterior.
- La Fase 1 tenía 85 pruebas aprobadas: 45 de backend y 40 de frontend. Esas pruebas siguen en la suite.

## Funcionalidad entregada

- Fase 0: estructura, salud, tema Claro/Oscuro/Sistema, dependencias y workflow de CI.
- Fase 1: autenticación, perfiles, roles base, correo, recuperación, Google OAuth preparado,
  aislamiento inicial y auditoría. La validación externa de Google y SMTP sigue pendiente.
- Fase 2.1: registro de empresas en estado pendiente, datos administrativos, RUC opcional,
  logotipo, varios dueños autorizados, selección de empresa y gestión administrativa global.
- Fase 2.2: sedes con ubicación, horario general, contacto, imagen principal y galería;
  alcance por empresa y por asignación, estados activos y soft delete de imágenes.
- Fase 2.3: personal existente e invitado, roles por empresa, asignación de sedes,
  invitaciones de un solo uso con token guardado como hash, vencimiento y revocación.
- Fase 2.4: planes SaaS configurables, solicitudes y verificación manual, periodos con
  precio histórico, registro independiente del pago SaaS, límites centralizados y vigencia.
- Fase 2.5: panel del dueño, consola global, administración de sedes asignadas y vista
  básica del cajero. Las interfaces usan los tokens aprobados y son responsive.
- Fase 2.6: pruebas de aislamiento, flujo de invitación, estados, pagos SaaS, precios
  históricos y límites bajo concurrencia en PostgreSQL.
- En Fase 2 no se implementaron canchas, tarifas, reservas, WebSockets de reservas, QR,
  kiosco ni caja.

## Fase 3A — gestión de canchas implementada

La entrega comprende la gestión administrativa de canchas asociadas a sedes existentes:

- Modelo `Cancha` y fotografías adicionales mediante `ImagenCancha`, ambas relaciones
  protegidas con `PROTECT`; conservar registros y retirar fotos sin borrado físico.
- Campos de identificación, sede, nombre, descripción, modalidad de fútbol, superficie,
  capacidad recomendada, techo, iluminación, características adicionales, imagen principal,
  estado y fechas de creación/actualización.
- Estados administrativos `activa`, `inactiva` y `mantenimiento`, independientes de la
  disponibilidad por horario.
- Lectura y escritura para dueños de empresa, administradores de sede asignados y
  superadministrador autorizado; el cajero consulta solamente canchas de sedes autorizadas.
  El alcance se deriva de la identidad y sus membresías/asignaciones, no de IDs del cliente.
- Endpoints de listado/registro, detalle/edición, cambio de estado, carga y retiro lógico de
  imágenes. El listado admite filtros por sede, modalidad, estado y nombre, y paginación.
- Límite SaaS de canchas aplicado en servidor y agregado sobre todas las sedes de la empresa;
  la política provisional de cupo está pendiente de aprobación en `DECISIONES.md`.
- Fotografías PNG, JPEG o WebP verificadas por firma y extensión, con máximo de 5 MiB.
  Los cambios quedan auditados.

No forman parte de Fase 3A las tarifas, horarios, cierres por disponibilidad,
calendarios, reservas, pagos, QR ni WebSockets de disponibilidad.

La funcionalidad está integrada en los paneles de dueño, administrador de sede, cajero
(solo lectura) y superadministrador. El frontend usa el cliente API y los tokens visuales
existentes; incluye filtros, paginación, alta, edición, fotografías, mensajes de carga/error,
confirmaciones y estados semánticos. El campo de modalidad admite valores enteros ampliables;
no se añadió un catálogo rígido.

## Fase 3B — horarios, cierres y disponibilidad operativa

- Horarios semanales estructurados por sede y cancha, varios intervalos diarios, cruce de
  medianoche y herencia de sede por día. Un día propio vacío queda cerrado; los días
  heredados siguen los cambios posteriores de la sede.
- Los intervalos propios de cancha deben quedar dentro del horario semanal de sede. El
  JSON `Sede.horario_general` anterior se conserva por compatibilidad, pero no alimenta
  estos servicios ni se edita desde el panel.
- Excepciones de cierre y ampliación con alcance de sede o cancha, motivo, responsable,
  marcas de tiempo, anulación sin borrar historial y auditoría de mutaciones.
- Consulta de bloques operativos completos de 60 minutos, en `America/Lima`, con filtro
  de rango inclusivo acotado y estado/motivo. Los cierres, estados inactivos y bloques
  pasados se devuelven deshabilitados. La respuesta declara `considera_reservas: false`;
  no representa disponibilidad para reservar.
- API autenticada y limitada por empresa/sede; el cajero solo consulta. Los jugadores no
  reciben un endpoint público en esta fase. La API calcula alcance desde la identidad y no
  confía en IDs enviados por el navegador.
- Panel integrado en dueño, administrador de sede, cajero (solo lectura) y consola global;
  usa tokens visuales Claro/Oscuro y conserva el estilo aprobado. Se retiró la edición del
  horario general de texto libre del formulario de sede.
- Se añadió el comando local `generar_datos_demo` con opt-in explícito, restricciones de
  entorno, datos ficticios identificados, repetición idempotente y credenciales locales
  ignoradas por Git. El modo de uso está en `docs/USUARIOS_PRUEBA.md`.

Las prioridades y convenciones de horario que requieren decisión del dueño se describen
como propuestas **PENDIENTES** en DECISIONES.md.

### Verificación final Fase 3A

- `pytest tests -q`: 69 aprobadas en 86,16 s.
- `npm run test:run`: 70 aprobadas en 18,38 s.
- `npm run build`: compilación correcta en 11,04 s.
- `manage.py check`: sin incidencias.
- `manage.py makemigrations --check --dry-run`: no detectó cambios pendientes.
- `ruff check .`: sin errores.
- Total de la verificación completa: 139 aprobadas, 0 fallidas y 0 omitidas.
- Durante la implementación también se ejecutaron pruebas focalizadas para los módulos
  afectados; sus comprobaciones finales están incluidas en las suites completas anteriores.

### Verificación final Fase 3B

- `pytest tests -q`: 90 aprobadas en 178,73 s.
- `npm run test:run`: 79 aprobadas en 10,11 s.
- Total automatizado: 169 aprobadas, 0 fallidas y 0 omitidas.
- `manage.py check`: sin incidencias; `makemigrations --check --dry-run`: sin cambios.
- `ruff check .`: sin errores.
- `npm run build`: compilación correcta (7,68 s de compilador).
- La suite de backend usó un directorio temporal aislado por un bloqueo de permisos en
  la carpeta temporal predeterminada de Windows.
- Las seis cuentas de demostración se autentican con las claves locales de
  `docs/USUARIOS_PRUEBA_LOCAL.md`, ignorado por Git.

## Migraciones

Aplicadas antes de Fase 2: empresas/0001_initial, usuarios/0001_initial,
usuarios/0002_perfiles_existentes y usuarios/0003_correopendiente_limiteacceso.

Generadas para Fase 2, de forma aditiva:

- empresas/0002_invitacionempleado_registroauditoria_and_more
- empresas/0003_invitacionempleado_sedes_registroauditoria_actor_and_more
- sedes/0001_initial
- suscripciones/0001_initial
- suscripciones/0002_alter_plansuscripcion_nombre_and_more

La migración aditiva de Fase 3A está en
`apps/canchas/migrations/0001_initial.py`. La comprobación de migraciones no detectó
cambios faltantes. Fase 3B añade `apps/horarios/migrations/0001_initial.py`.

`showmigrations` confirmó las migraciones de Fase 2, 3A, 3B, `tarifas.0001_initial` y
`canchas.0002_cancha_publicada` aplicadas en la base local de desarrollo. Se comprobó que
contiene solo el fixture marcado de demostración; no se
reinició ni se eliminó ninguna base de datos. Pytest crea y migra una base temporal aparte.

## Validación local registrada — Fase 2

- Backend: 59 aprobadas, 0 fallidas.
- Frontend: 53 aprobadas, 0 fallidas.
- Total: 112 aprobadas, 0 fallidas, 0 omitidas.
- Django check: sin incidencias.
- makemigrations --check --dry-run: sin cambios pendientes.
- Ruff: sin errores.
- Vite build: compilación correcta.
- GitHub Actions incluye pytest completo, Vitest, Django check, migraciones y build;
  no se afirma que el workflow remoto se haya ejecutado.

Los resultados de Fase 2 y 3A son históricos; la verificación final de Fase 3B está registrada
arriba y en `PLAN_PRUEBAS.md`.

Los comandos y cobertura están en PLAN_PRUEBAS.md. La revisión en navegador contra
un servicio externo no se hizo para Google OAuth ni para SMTP.

## Pendientes

1. Credenciales y retorno reales de Google OAuth.
2. Servicio SMTP y entrega a una bandeja real.
3. Ejecución remota de GitHub Actions.
4. Confirmación de las propuestas comerciales de DECISIONES.md, en particular la
   semántica de límites nulos, gracia, duración de invitaciones, periodos suspendidos y propuestas de prioridad de tarifas.
5. Fase 4B — disponibilidad en tiempo real con Django Channels/Redis.

## Continuidad

Leer AGENTS.md, AUTENTICACION.md, ARQUITECTURA.md, MODELO_DATOS.md,
DECISIONES.md y PLAN_PRUEBAS.md antes de continuar.


## Fase 3C: tarifas y cálculo de precios — implementada

- `apps.tarifas.ReglaTarifa` configura precios Decimal/PEN por cancha, tipo, días o fechas,
  horario y vigencia; desactivar una regla conserva su historial y cada cambio se audita.
- API para listar, crear, editar y activar/desactivar reglas con validación de empresa y
  sede. El cajero consulta; el superadministrador tiene acceso global auditado.
- El cálculo reutilizable comprueba bloques operativos, cierres y tarifas faltantes, y
  devuelve importes por bloque, subtotal, total y moneda. Se mantiene
  `considera_reservas: false`.
- El panel permite administrar reglas y consultar precios por cancha; las cuentas locales
  de prueba incluyen 22 tarifas demostrativas en dos empresas.
- Las prioridades comerciales y la zona horaria configurable por sede siguen pendientes
  de aprobación en DECISIONES.md.

## Fase 3D: calendario, integración y validación — implementada

- Calendario operativo diario/semanal en los paneles de dueño, administrador de sede,
  cajero (solo consulta) y superadministrador. Consume bloques del endpoint integrado con
  horarios, cierres, estado de cancha y tarifas; distingue ampliaciones excepcionales.
- Selección de hasta 24 bloques consecutivos y cotización preliminar a través del servicio
  Decimal del backend. No reserva ni bloquea; `considera_reservas: false` permanece explícito.
- `Cancha.publicada` incorpora publicación voluntaria y desactivada por defecto. Los
  endpoints públicos muestran únicamente los campos aprobados, precios/bloques permitidos y
  no exponen contactos o información empresarial privada.
- Se conserva `America/Lima` como zona técnica actual; zona por sede, prioridad de reglas,
  horarios diurno/nocturno y demás propuestas siguen pendientes de decisión comercial.
- La migración aditiva `canchas.0002_cancha_publicada` agrega el control de publicación.
  Los datos locales de demostración publican una cancha de cada empresa y preservan las seis
  cuentas existentes.
- Resultados exactos de suites y validaciones al cierre de esta fase: `docs/PLAN_PRUEBAS.md`.
  Al cierre de Fase 3D, las reservas, retenciones, pagos y WebSockets seguían fuera de
  alcance; las retenciones se implementaron después en Fase 4A.

## Fase 4A — motor de reservas y retención temporal

Implementa la reserva real sobre horarios, excepciones y tarifas existentes. Una solicitud
autenticada de jugador genera una retención por 1–24 bloques consecutivos, importe y adelanto
calculados con Decimal, snapshot de precio, código único e historial. /mis-reservas permite
consultar o cancelar una retención propia.

PostgreSQL evita solapamientos con transacción atómica, bloqueo de la cancha, bloques
horarios y una restricción de exclusión GiST para los intervalos no liberados. Los reintentos
por clave UUID son idempotentes. La disponibilidad pública y administrativa ahora considera
retenciones y mantiene el aislamiento por empresa/sede; la consulta operativa de 3B conserva
considera_reservas: false.

El plazo técnico inicial configurable es de 15 minutos y sigue PENDIENTE de aprobación
comercial. El comando expirar_retenciones actualiza estados y libera bloques aunque no haya
usuarios conectados; el despliegue debe programarlo en el servidor. No se implementaron pagos,
WebSockets, WhatsApp, confirmación ni QR.

El frontend reutiliza el calendario matricial basado en Stitch y los controles compartidos de
tabla, modal y botón, adaptados a la paleta y tipografías oficiales de AlToque. El generador
local conserva las seis cuentas y sus contraseñas existentes, agrega tres reservas demo y
migra la guía local anterior sin revelar ni reemplazar credenciales.

Resultados completos de backend, frontend y verificaciones estáticas: ver la sección Fase 4A
de docs/PLAN_PRUEBAS.md.

## Fase 4B — disponibilidad en tiempo real

Channels/ASGI enruta `ws/disponibilidad/` con sesiones existentes, validación de origen y
autorización por cancha, publicación, empresa y sede. Los grupos filtran por cancha/fecha y
los payloads mínimos solo contienen tipo, cancha, fecha y motivo. Los cambios de retención,
horario, excepción, tarifa, cancha y sede se publican después del commit; PostgreSQL continúa
siendo la fuente oficial.

Los calendarios público y administrativo usan un composable compartido, reconexión progresiva
limitada, reconsulta REST, indicador accesible y actualización manual. Una selección que deja
de estar disponible se invalida con aviso visible. Se añadió una segunda cuenta jugador al
seeder idempotente para probar dos sesiones independientes sin reemplazar claves locales.
Playwright ya está configurado para Chromium y automatiza retención + cancelación entre dos
contextos de navegador.

Desarrollo local permite InMemory con un solo proceso; producción requiere Redis configurado
por `REDIS_URL` o `REDIS_HOST`/`REDIS_PORT`. La prueba que requiere servidor Redis real se
omite cuando el servicio no está disponible en el entorno. El proceso de vencimientos puede
ejecutarse continuamente con `python manage.py expirar_retenciones --continuo --intervalo 60`;
la retención configurable de 15 minutos sigue pendiente de aprobación comercial.

Resultados completos de pytest, Vitest, Playwright, Django check, Ruff, migraciones y build:
ver la sección Fase 4B de `docs/PLAN_PRUEBAS.md`. No se implementaron pagos, comprobantes,
confirmación de reserva, WhatsApp, correo de reserva ni QR.

## Fase 4C — pagos Yape/Plin y verificación manual

Implementa métodos de pago separados por sede (Yape, Plin y transferencia), solicitud de
adelanto mínimo/total/saldo a partir del precio histórico, enlace WhatsApp prellenado y
declaración manual del comprobante. El equipo autorizado revisa el importe y referencia desde
la cola de pagos; las aprobaciones y rechazos quedan auditados. No se automatiza la aprobación
por abrir WhatsApp o declarar el envío.

El jugador consulta `/mis-reservas/<código>/pago`. Dueño o administrador de sede configura los
medios en **Pagos**; cajero revisa la cola en `/panel/cajero` → **Pagos**. La aprobación deja
la reserva en `pendiente_confirmacion`; QR, correo y confirmación final quedan para 4D.
`RESERVA_REVISION_PAGO_MINUTOS=15` es provisional y configurable. Pagos están deshabilitados
por defecto en producción hasta aprobar las decisiones comerciales registradas en
`docs/DECISIONES.md`.

El generador local conserva las cuentas y sus contraseñas estables, y añade 12 medios y pagos
ficticios identificados. Las cuentas, referencias y números de demo no se deben usar para
pagos reales. Ver escenarios reproducibles en `docs/USUARIOS_PRUEBA.md` y resultados exactos
de las suites en `docs/PLAN_PRUEBAS.md`.
