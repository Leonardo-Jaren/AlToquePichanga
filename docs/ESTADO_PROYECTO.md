# Estado del Proyecto — AlToque Pichanga

Actualizado: 18 de octubre de 2026 (America/Lima).
Fase 2: **completada**. Fases 3A — gestión de canchas y 3B — horarios, cierres y disponibilidad base: **implementadas**. La verificación final de Fase 3B está registrada en PLAN_PRUEBAS.md.
Siguiente fase: **Fase 3C — tarifas y cálculo de precios** (pendiente de autorización).

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

`showmigrations` confirmó las migraciones de Fase 2, 3A y 3B aplicadas en la base local
de desarrollo. Se comprobó que contiene solo el fixture marcado de Fase 3B; no se
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
   semántica de límites nulos, gracia, duración de invitaciones y periodos suspendidos.
5. Siguiente entrega: Fase 3C — tarifas y cálculo de precios, pendiente de autorización.

## Continuidad

Leer AGENTS.md, AUTENTICACION.md, ARQUITECTURA.md, MODELO_DATOS.md,
DECISIONES.md y PLAN_PRUEBAS.md antes de continuar.

