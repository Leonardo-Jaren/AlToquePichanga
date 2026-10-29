# Roadmap de Desarrollo — AlToque Pichanga

Plan de trabajo por fases. Las Fases 2, 3A–3D, 4A, 4B y 4C están implementadas; la siguiente
entrega es Fase 4D.

## Fase 0: Inicialización y entorno base — completada

- Estructura backend/frontend/docs, PostgreSQL, pytest, Ruff, Vue, Vite, Tailwind y CI.
- Tokens oficiales de marca, salud de API y selector de tema.
- La configuración externa del despliegue continúa pendiente.

## Fase 1: Autenticación, usuarios y roles base — completada

- Registro, ingreso, sesión, CSRF, recuperación, verificación, perfil y límites.
- auth.User conservado; perfil y membresías empresariales en español.
- Google OAuth con validación local del flujo; faltan credenciales reales.
- Resultados y detalles en ESTADO_PROYECTO.md, AUTENTICACION.md y PLAN_PRUEBAS.md.

## Fase 2: Empresas, sedes, empleados y suscripciones SaaS — completada

- Empresas propietarias múltiples, estados comerciales y revisión global.
- Sedes aisladas por empresa y administradores de sede limitados a asignaciones.
- Invitaciones seguras, roles, revocación y límite de último dueño.
- Planes SaaS, solicitudes y revisión manual; vigencia y límites desde el backend.
- Paneles del dueño y plataforma; pantalla básica de cajero.
- La lista completa de modelos, endpoints, reglas y pruebas está en MODELO_DATOS.md,
  ARQUITECTURA.md y PLAN_PRUEBAS.md.

## Fase 3A: Gestión de canchas — completada y verificada

- Gestionar canchas dentro de las sedes existentes, con fotografías adicionales,
  características técnicas y estados `activa`, `inactiva` y `mantenimiento`.
- Dueños y administradores de sede asignados pueden administrar dentro de su alcance;
  cajeros solo consultan sus sedes y el superadministrador usa su acceso global auditado.
- Listado filtrable y paginado, alta, detalle, edición, cambio de estado y administración
  de fotografías sin borrado físico.
- Aplicar el máximo SaaS total por empresa con concurrencia segura. La regla provisional
  de estados que consumen cupo está marcada como supuesto pendiente en DECISIONES.md.
- Validar imágenes PNG/JPEG/WebP por firma y extensión, hasta 5 MiB.
- Esta fase no incluye tarifas ni calendario/disponibilidad.
- Verificación final: 69 pruebas backend y 70 frontend aprobadas; compilación, Django,
  migraciones y Ruff correctos. Detalle y tiempos en PLAN_PRUEBAS.md.

## Fase 3B: Horarios, cierres y disponibilidad base — implementada y verificada

- Horario semanal por sede y cancha, varios intervalos al día, cruces de medianoche y
  herencia de la sede por día; los intervalos propios respetan el marco operativo de sede.
- Cierres y ampliaciones excepcionales, con prioridad de cierre, historial preservado,
  motivo y auditoría. Las convenciones pendientes siguen identificadas en DECISIONES.md.
- Consulta acotada de bloques de 60 minutos en `America/Lima`, aplicando excepciones y
  estados administrativos; la respuesta es solo operativa y no incorpora reservas.
- Panel integrado para dueño, administrador asignado, cajero en modo lectura y plataforma.
- Generador local idempotente de usuarios y datos de demostración con límites de entorno.
- Verificación final: consultar resultados exactos en PLAN_PRUEBAS.md. Sin tarifas,
  reservas, retenciones, pagos ni WebSockets.

## Fase 3C: Tarifas y cálculo de precios — implementada

- Reglas por cancha con importes Decimal/PEN, días, fechas especiales, horario, vigencia y
  activación lógica, con aislamiento multiempresa y auditoría.
- Cálculo reutilizable por bloques operativos con total decimal, cierres y tarifas faltantes.
- Panel de reglas y precios, consulta de cajero y datos demo locales en dos empresas.
- Las prioridades y convenciones comerciales continúan pendientes de aprobación en
  DECISIONES.md. Sin descuentos, reservas, retenciones ni pagos.

## Fase 3D: Calendario visual, integración y validación — implementada

- Calendario diario y semanal integrado con horarios, excepciones, cierres, estado de cancha,
  tarifas y cotización preliminar reutilizando los servicios de 3B/3C.
- Publicación explícita de canchas, apagada por defecto, con consultas públicas acotadas y
  aislamiento administrativo multiempresa aplicado en el backend.
- Al cierre de Fase 3D, las cotizaciones aún no creaban reservas ni bloqueaban horarios y la
  disponibilidad declaraba `considera_reservas: false`; Fase 4A agregó retenciones después.
- Las decisiones comerciales de tarifas y zona horaria continúan pendientes en DECISIONES.md.

## Fase 4A: Motor de reservas y retención temporal — implementada

- Solicitudes propias, consulta y cancelación de retenciones, disponibilidad pública real y
  disponibilidad administrativa limitada por empresa/sede.
- Retención configurable (`RESERVA_RETENCION_MINUTOS`, provisional 15 minutos), transición
  centralizada e historial auditable; `expirar_retenciones` libera horarios sin depender de
  que el jugador tenga abierta la página.
- Bloques consecutivos y tarifas históricas con `Decimal`, adelanto mínimo calculado del 50%
  y vencimiento/cancelación con liberación de horarios.
- PostgreSQL protege los intervalos activos con transacción, bloqueo por cancha y restricción
  de exclusión GiST; los reintentos de cliente son idempotentes.
- Frontend público y pantalla `/mis-reservas`; tabla administrativa reutilizable con
  `TablaBase.vue`, `ModalBase.vue` y `BotonBase.vue`. La vista de administración adapta la
  matriz horaria de Stitch a los tokens oficiales de AlToque y Archivo Black/Outfit.
- Fuera de alcance de esta subfase: WebSockets, pagos, WhatsApp, confirmación pagada y QR.

## Fase 4B: Disponibilidad en tiempo real — implementada

- Django Channels/ASGI, suscripciones seguras por cancha/fecha, grupos de cambios de calendario
  y Redis para despliegues con varios procesos; desarrollo local puede usar InMemory.
- Retenciones creadas, canceladas y vencidas, además de cambios de horario/tarifa/cancha/sede,
  emiten eventos mínimos después del commit. PostgreSQL sigue siendo la autoridad.
- Vue reconecta con espera progresiva limitada, reconsulta la API REST y permite actualización
  manual; la E2E comprueba dos sesiones independientes sin recargar.
- La integración contra un servidor Redis real queda sin verificar en este entorno porque no
  hay servicio Redis disponible; el test de integración lo indica como omitido.

## Fase 4C: Pagos de reserva, WhatsApp y verificación manual — implementada

- Medios Yape, Plin y transferencia independientes por sede, más adelanto mínimo, pago total y
  saldo calculados desde la cotización histórica de la reserva con `Decimal`.
- Enlace `wa.me` con texto prellenado; el jugador adjunta manualmente la captura y declara el
  envío por separado. Ninguna de esas acciones aprueba automáticamente el pago.
- Cola filtrable y revisión en modal para personal con alcance autorizado, con auditoría,
  referencia, importe verificado, rechazo justificado e historial.
- Los pagos de reservas están separados de las suscripciones SaaS. No hay pasarela, caja,
  correo de confirmación ni QR en esta fase.
- La revisión provisional y el interruptor de pagos de producción se documentan como
  decisiones pendientes en `DECISIONES.md`.

## Fase 4D: Confirmación y ticket de reserva — siguiente

- Completar el flujo después del pago aprobado, con confirmación final, notificación por
  correo y QR firmado/aleatorio visible solo para reservas confirmadas.
- Revisar política comercial de vencimiento, cancelación, conciliación y comunicación antes
  de habilitar el flujo en producción.

## Fase 5: Kiosco presencial y caja

- Venta presencial, productos, turnos, ingresos/egresos, cierre y conciliación.
- Control de stock solo después de aprobar el alcance; no duplicar pagos en caja.

## Fase 6: Catálogo público

- Directorio multiempresa de sedes y canchas, búsqueda y filtros.
- Publicar únicamente datos explícitamente definidos para el catálogo.

## Fase 7: Auditoría y preparación de producción

- Revisión de seguridad, consultas, permisos por HTTP y tareas internas.
- Pruebas de carga y revisión operativa de almacenamiento, colas y respaldos.

Google OAuth real, SMTP real y CI remoto son validaciones externas pendientes y no
se contabilizan como capacidades comprobadas.

