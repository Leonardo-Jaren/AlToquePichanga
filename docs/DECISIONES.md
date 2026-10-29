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

Resolver las propuestas comerciales antes de activar empresas reales. Las Fases 3C, 3D, 4A y
4B están implementadas con las convenciones provisionales documentadas aquí; la siguiente
subfase es 4C (pagos y verificación manual).


## Fase 3C — Propuestas de tarifas pendientes

14. **Rangos diurnos/nocturnos — PROPUESTA PENDIENTE DE APROBACIÓN.** Cada regla almacena
    su horario explícito o se marca como aplicable todo el día; no se impuso una hora
    comercial universal que separe día y noche.

15. **Prioridad — PROPUESTA PENDIENTE DE APROBACIÓN.** La convención técnica actual evalúa
    fecha especial > feriado > fin de semana > diurna/nocturna. Reglas activas ambiguas de
    igual prioridad se rechazan al crear, editar o activar.

16. **Bloque que cruza dos tarifas — CONVENCIÓN TÉCNICA PROPUESTA.** Cada bloque completo de
    60 minutos usa la regla vigente en su hora de inicio local; nunca se parte un bloque.
    Hoy el servicio emplea `TIME_ZONE` (`America/Lima`). Confirmar si cada sede necesita una
    zona configurable, ya que el modelo actual de Sede no tiene un campo de zona horaria.

17. **Tarifa faltante y bloques cerrados — CONVENCIÓN TÉCNICA PROPUESTA.** Un bloque cerrado
    no muestra precio y el cálculo lo rechaza. Si falta una regla activa, disponibilidad
    informa `tarifa_estado: sin_configurar`; el cálculo devuelve un error comprensible y no
    usa un precio cero ni uno inventado.

18. **Vigencia e histórico — PROPUESTA PENDIENTE.** Los extremos de vigencia son inclusivos.
    Cambiar o desactivar una regla afecta consultas futuras. La futura fase de reservas
    deberá guardar una copia del importe confirmado; Fase 3C no crea reservas ni snapshots.

19. **Alcance y demostración.** Los precios de prueba se añaden solo con el generador local
    opt-in, no representan valores comerciales y no se aplican a producción. Descuentos,
    cupones, puntos, reservas, retenciones y pagos siguen fuera de esta fase.

## Fase 3D — decisiones que requieren autorización

La integración conserva sin convertir en política comercial aprobada las convenciones de
prioridad y vigencia ya implementadas. Se identifican los siguientes puntos para revisión:

20. **Prioridad de tarifas.** La precedencia técnica actual es especial > feriado > fin de
    semana > diurna/nocturna. Confirmar el orden comercial deseado.
21. **Corte día/noche.** No existe una hora universal en el código: cada regla guarda un
    rango explícito. Confirmar si se desea fijar un corte compartido por sede.
22. **Bloque que cruza tarifas o medianoche.** Un bloque usa la regla de su hora de inicio
    local; el selector admite la secuencia entre días. Confirmar esta convención para futuras
    reservas.
23. **Zona horaria por sede.** Hoy se usa `TIME_ZONE=America/Lima`, porque Sede aún no guarda
    zona. Confirmar si cada sede deberá definir una zona antes de abrir varias regiones.

Hasta que se aprueben, estos comportamientos permanecen como convenciones técnicas
provisionales y centralizadas; la interfaz consulta el resultado del backend y no reimplementa
prioridades ni cálculo.

## Fase 4A — decisiones y convenciones pendientes

24. **Duración de retención — PENDIENTE de aprobación comercial.** El backend usa el valor
    configurable RESERVA_RETENCION_MINUTOS=15 solo como valor provisional de desarrollo.
    No se presenta como política del producto ni se fija como constante en el servicio.
    El vencimiento se procesa con una tarea del servidor; despliegue debe programar
    python manage.py expirar_retenciones (propuesta: cada minuto).

25. **Adelanto calculado — regla técnica ya establecida.** El sistema calcula el mínimo del
    50% con Decimal, guarda el snapshot de precio y todavía no acepta pagos ni confirma la
    reserva. La integración de pago y el saldo quedan para una fase posterior.

26. **Cancelación de retención — alcance acotado de Fase 4A.** El jugador puede liberar una
    retención propia que siga vigente. Si ya venció, el backend la marca vencida; no se
    aplican devoluciones, penalidades ni reglas de cancelación de una reserva confirmada.
    Las políticas comerciales generales siguen pendientes.

27. **Intervalos nocturnos y zona.** La reserva conserva America/Lima de la configuración
    actual y usa el mismo cálculo horario/tarifario existente, incluyendo intervalos que
    cruzan medianoche. La zona configurable por sede y la convención comercial de tarifas
    siguen pendientes conforme a las decisiones 11, 16 y 23.

28. **Datos demo de reservas.** El seeder agrega tres registros ficticios identificados por
    clave UUID estable, asociados al jugador y a canchas con [DEMO ALTOQUE]. Las retenciones
    activas duran el valor provisional; una retención vencida muestra la liberación e
    historial. El seeder no crea dos intervalos activos superpuestos ni registros de pago.

Fase 4B ya implementa avisos WebSocket de disponibilidad. Fase 4A no creó pagos, QR,
WhatsApp, correos de confirmación o flujos contables; estos pertenecen a Fase 4C y requieren
su autorización antes de implementarse.

## Fase 4B — convenciones técnicas

29. **Grupos WebSocket.** El backend autoriza cada cancha solicitada contra publicación,
    sesión y alcance de sede; suscripciones limitadas a 24 canchas y siete fechas. Los eventos
    incluyen únicamente tipo, cancha, fecha y motivo, sin datos personales ni importes.
30. **Canal distribuido.** Desarrollo local con `DEBUG=True` puede usar InMemory en un único
    proceso ASGI. Producción requiere Redis (`REDIS_URL` o `REDIS_HOST`/`REDIS_PORT`) y falla
    al iniciar si se desactiva Redis con `DEBUG=False`.
31. **Vencimientos.** El proceso continuo puede ejecutarse con
    `python manage.py expirar_retenciones --continuo --intervalo 60`; conserva la retención
    configurable de 15 minutos como propuesta comercial pendiente.
32. **Redis real — verificación pendiente del entorno.** La suite Channels pasó con la capa
    local; la prueba de integración Redis se omite si no hay servidor accesible. El entorno de
    desarrollo utilizado para esta fase no tenía Redis disponible.

## Fase 4C — pagos manuales pendientes de decisión comercial

33. **Duración de revisión — PENDIENTE de aprobación.** `RESERVA_REVISION_PAGO_MINUTOS` usa
    provisionalmente 15 minutos, configurable por entorno y sin fijar una política para
    producción. Al declarar el comprobante, la retención se extiende como máximo una vez.
    Si no se completa la confirmación posterior antes del vencimiento, se libera el horario;
    todo pago ya aprobado queda preservado y marcado para conciliación manual.

34. **Activación en producción — BLOQUEADA hasta aprobación.** `PAGOS_RESERVA_HABILITADOS`
    usa `DEBUG` como valor predeterminado local y queda `False` fuera de desarrollo. Deben
    aprobarse duración de revisión, operación ante pagos tardíos, datos oficiales de cada sede
    y las condiciones visibles al jugador antes de activarlo.

35. **Comprobante y WhatsApp — límite técnico explícito.** El enlace `wa.me` prepara un texto;
    el jugador debe adjuntar la imagen manualmente. Abrirlo o declarar el envío no es prueba
    de pago. Un empleado autorizado compara la operación y registra el resultado. No se usan
    API de WhatsApp, pasarelas ni datos bancarios de AlToque.

36. **Alcance de la Fase 4C.** La aprobación conserva la reserva en `pendiente_confirmacion`;
    el QR, el correo de confirmación y la transición final pertenecen a Fase 4D. No se habilita
    cancelación pagada ni devolución automática en esta entrega.
