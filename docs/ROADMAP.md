# Roadmap de Desarrollo — AlToque Pichanga

Plan de trabajo por fases. Las Fases 2, 3A y 3B están implementadas; la siguiente entrega
es Fase 3C, pendiente de autorización.

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

## Fase 3C: Tarifas y cálculo de precios — pendiente de autorización

- Proponer antes de implementar los rangos diurnos/nocturnos, cálculo por bloque y
  almacenamiento histórico de la tarifa aplicada.
- No asumir políticas comerciales de fines de semana o feriados.

## Fase 4: Reservas y disponibilidad en tiempo real

- Reservas por bloques de una hora, calendario y consumo de la disponibilidad definida en 3B.
- Transiciones de estado, retención configurable y tarea de expiración.
- Restricciones PostgreSQL contra duplicidad, transacciones atómicas y Django Channels
  con Redis; eventos informativos sin datos privados.

## Fase 5: Pagos de reserva, WhatsApp y QR

- Adelanto, saldo, comprobante enviado manualmente a WhatsApp de la sede.
- Validación de pago por empleado autorizado, auditoría y QR habilitado al confirmar.
- Sin pasarela ni cobro centralizado del SaaS en el MVP.

## Fase 6: Kiosco presencial y caja

- Venta presencial, productos, turnos, ingresos/egresos, cierre y conciliación.
- Control de stock solo después de aprobar el alcance; no duplicar pagos en caja.

## Fase 7: Catálogo público

- Directorio multiempresa de sedes y canchas, búsqueda y filtros.
- Publicar únicamente datos explícitamente definidos para el catálogo.

## Fase 8: Auditoría y preparación de producción

- Revisión de seguridad, consultas, permisos por HTTP y tareas internas.
- Pruebas de carga y revisión operativa de almacenamiento, colas y respaldos.

Google OAuth real, SMTP real y CI remoto son validaciones externas pendientes y no
se contabilizan como capacidades comprobadas.

