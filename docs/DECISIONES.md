# Decisiones y propuestas pendientes — AlToque Pichanga

Las siguientes conductas tienen una implementación central para que puedan revisarse y
cambiarse sin alterar datos históricos. Su presencia en el código no representa aprobación
comercial del dueño del proyecto.

## Pendientes de confirmación

1. **Límites nulos.** En la implementación, null significa que el plan no fija un máximo;
   cero significa que no se permite crear ese recurso. Propuesta: conservar esa distinción.
   No se publicaron planes ni valores comerciales por defecto.

2. **Días de gracia SaaS.** El valor inicial es cero. El superadministrador puede
   modificarlo en la consola. Durante la gracia, las operaciones que requieren vigencia
   permanecen habilitadas. Propuesta: aprobar el valor inicial de cero días o establecer
   una política comercial antes de activar empresas reales.

3. **Vencimiento de invitaciones.** La duración se configura mediante
   INVITACION_DIAS_VIGENCIA y el valor técnico inicial es siete días. Propuesta:
   confirmar duración y si el recordatorio de invitación será necesario.

4. **Cálculo de periodos.** El periodo es inclusivo: se suma la periodicidad a la fecha
   de inicio usando el día equivalente con ajuste al último día disponible del mes y se
   resta un día. Por ejemplo, un periodo mensual que inicia el 31 de enero termina el
   27 de febrero en un año no bisiesto. Propuesta: confirmar esta convención antes de
   registrar suscripciones reales.

5. **Suspensión y renovación.** Una suspensión impide operar y no prolonga el periodo ya
   comprado. Una renovación comienza después del vencimiento vigente; la API rechaza
   periodos superpuestos. Propuesta: confirmar si una suspensión debe congelar tiempo o
   mantener la fecha de vencimiento original.

6. **RUC opcional.** Se permite registrar empresas sin RUC; un RUC informado debe tener
   once dígitos y ser único. La obligatoriedad futura queda pendiente de decisión.

7. **Aprobación separada.** Aprobar una empresa y aprobar su suscripción son acciones
   independientes. Un pago o solicitud no activa automáticamente ninguna de las dos.
   Esta separación se conserva como regla de seguridad.

8. **Cupo SaaS de canchas — SUPUESTO PENDIENTE DE APROBACIÓN.** La implementación de Fase 3A
   aplica `maximo_canchas` al total de canchas de todas las sedes de una empresa.
   `activa` y `mantenimiento` consumen cupo; `inactiva` lo libera y su reactivación vuelve
   a comprobar el límite. El control ya está implementado y probado, pero eso no representa
   aprobación comercial del dueño. Ajustar la regla cuando exista confirmación.

9. **Cierres y ampliaciones — PROPUESTA PENDIENTE.** El cálculo actual da prioridad a un
   cierre frente al horario semanal y a cualquier ampliación que se solape; los cierres de
   sede alcanzan todas sus canchas. Las excepciones activas del mismo tipo y alcance que se
   solapan se rechazan; un cierre y una ampliación pueden coincidir, y el cierre gana.
   Confirmar esta política antes de considerar la disponibilidad definitiva para reservas.

10. **Alcance de una ampliación de sede — PROPUESTA PENDIENTE.** Hoy extiende el horario
    operativo de todas las canchas de esa sede. Una ampliación asociada directamente a una
    cancha se valida dentro del horario efectivo de la sede. Confirmar si una ampliación de
    sede debe abrir todas las canchas o solo las que heredan el horario en ese día.

11. **Cruce de medianoche — CONVENCIÓN TÉCNICA PENDIENTE DE CONFIRMACIÓN.** Si la hora de
    cierre es menor que la de apertura, el intervalo termina al día siguiente; horas iguales
    se rechazan. Confirmar que esta convención cubre los horarios hasta las 00:00 deseados.

12. **Bloques operativos — PROPUESTA TÉCNICA PENDIENTE.** La implementación genera bloques
    completos de 60 minutos consecutivos desde el inicio de cada tramo operativo; omite el
    tramo final menor a una hora y marca como cerrados los bloques que intersectan un cierre.
    La disponibilidad sigue sin consultar reservas. Confirmar si se requiere otra alineación
    de bloques o mostrar explícitamente intervalos parciales.

13. **Rango de consulta — LÍMITE TÉCNICO PENDIENTE.** El máximo inclusivo inicial es 31
    días y se configura con `MAX_DIAS_CONSULTA_DISPONIBILIDAD`. Confirmar el rango de producto
    antes de abrir esta consulta en un catálogo público.

## Valores que no se han inventado

No se configuraron precios, prueba gratuita, límites numéricos de planes, pasarela,
comisión, periodicidad obligatoria, facturación electrónica o acceso de producción.
`maximo_canchas` existe en el modelo del plan y Fase 3A contempla su aplicación a canchas;
el criterio de qué estados ocupan el cupo permanece como supuesto pendiente.

## Continuidad

Resolver los puntos comerciales antes de activar empresas reales. Fase 3A cubre la gestión
administrativa de canchas; Fase 3B, horarios, cierres y disponibilidad operativa. Las
propuestas de esta sección no equivalen a aprobación del dueño. Tarifas, reservas y pagos
siguen fuera del alcance entregado y requieren sus respectivas fases autorizadas.

