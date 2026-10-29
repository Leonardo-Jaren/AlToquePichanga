# Modelo de datos — Fases 1–4C

Se conserva auth.User y AUTH_USER_MODEL. Las tablas y campos nuevos de negocio están en
español. PostgreSQL compartido aplica restricciones; servicios y repositorios establecen
el alcance autorizado antes de cada lectura y cambio.

## Identidad y empresa

| Modelo / tabla | Datos y relaciones |
|---|---|
| PerfilUsuario / usuarios_perfiles | User 1:1, correo, verificación y fecha |
| IdentidadGoogle / usuarios_identidades_google | User 1:1 e identificador Google único |
| Empresa / empresas | Razón social, nombre comercial, RUC opcional, descripción, logotipo, contacto, estado, activa y fecha |
| MembresiaEmpresa / empresas_membresias | User FK, Empresa FK, rol, activa y fecha |
| AccesoPlataforma / empresas_accesos_plataforma | Actor, empresa opcional, acción y fecha para lecturas globales |
| RegistroAuditoria / empresas_registros_auditoria | Actor, empresa opcional, recurso, identificador, acción, datos y fecha |
| InvitacionEmpleado / empresas_invitaciones_empleado | Empresa, correo, rol, sedes autorizadas, creador, hash de token y fechas |

Una empresa puede tener varios dueños autorizados. Un usuario puede ser dueño de varias
empresas y tener un rol diferente en otra empresa. Roles de membresía: dueno,
administrador_sede y cajero. El superadministrador es la capacidad global de auth.User,
no un rol empresarial asignable.

EstadoEmpresa: pendiente, activa, rechazada o suspendida. La columna activa se conserva
por compatibilidad con Fase 1 y los servicios de cambio de estado mantienen ambas coherentes.
No existe un endpoint para eliminar físicamente una empresa.

## Sedes y personal

| Modelo / tabla | Datos y relaciones |
|---|---|
| Sede / sedes | Empresa FK PROTECT; nombre, descripción, dirección, departamento, provincia, distrito, latitud, longitud, contactos, horario_general JSON, imagen principal, activa y fechas |
| AsignacionSede / sedes_asignaciones | Sede FK PROTECT, MembresiaEmpresa FK PROTECT, activa y fecha |
| ImagenSede / sedes_imagenes | Sede FK PROTECT, archivo, descripción, orden, activa y fecha |

Latitud y longitud deben estar ambas vacías o ambas presentes y dentro de su rango.
Horario general acepta días de la semana en español y textos breves. Las imágenes retiradas
se marcan inactivas; no se borran sus filas. Las imágenes aceptadas son PNG, JPEG o WebP
por firma y con máximo de 5 MiB.

El dueño administra las sedes de sus empresas. El administrador de sede necesita una
AsignacionSede activa para consultar y modificar una sede. Una membresía de cajero no
concede edición. El backend comprueba que una sede seleccionada pertenezca a la misma
empresa que la membresía; el navegador nunca autoriza ese vínculo.

Las invitaciones guardan un SHA-256 del token aleatorio y no el token original. El token
vence, se acepta una vez o se revoca. La pertenencia al correo se valida contra
PerfilUsuario al aceptar. Las invitaciones y membresías no son eliminables desde estos flujos.

## Canchas — Fase 3A (implementada y verificada)

| Modelo / tabla | Datos y relaciones |
|---|---|
| Cancha / canchas | Sede FK PROTECT; nombre, descripción, modalidad, superficie, capacidad recomendada, techada, iluminación, características, imagen principal, estado y fechas |
| ImagenCancha / canchas_imagenes | Cancha FK PROTECT, archivo, descripción, orden, activa y fechas |

Una cancha pertenece a una sola sede. Los estados administrativos son `activa`, `inactiva`
y `mantenimiento`; no representan disponibilidad por horario. Ni las canchas ni sus fotos
se eliminan físicamente; el retiro de una foto conserva su fila y la marca inactiva.
Las imágenes admitidas son PNG, JPEG o WebP verificados por firma y extensión, con un
tamaño máximo de 5 MiB.

La modalidad es un entero positivo de 1 a 32767 que se presenta como cantidad de jugadores
(por ejemplo, fútbol 5, 7 u 11); no hay un catálogo rígido. La superficie es texto de hasta
80 caracteres, por lo que admite valores adicionales. La capacidad recomendada es opcional.

El alcance se obtiene desde las sedes autorizadas: dueños de empresa y administradores de
sede asignados leen y escriben dentro de su alcance; el superadministrador autorizado tiene
alcance global; el cajero solo lee las canchas de sedes autorizadas. Un identificador de
sede o cancha recibido del cliente no concede acceso.

El máximo de canchas del plan se aplica al total de la empresa, contando `activa` y
`mantenimiento` en todas sus sedes. `Inactiva` libera cupo; al reactivarla se valida el
límite dentro de una transacción concurrentemente segura. Esta regla es un **supuesto
pendiente de aprobación**, registrado en DECISIONES.md.

## Horarios y excepciones — Fase 3B

| Modelo / tabla | Datos y relaciones |
|---|---|
| HorarioSede / horarios_sede | Sede 1:1 PROTECT, indicador de configuración y fechas |
| IntervaloHorarioSede / horarios_sede_intervalos | Horario FK CASCADE, día (0=lunes…6=domingo), apertura y cierre |
| HorarioCancha / horarios_cancha | Cancha 1:1 PROTECT, herencia completa o por días, indicador de configuración y fechas |
| IntervaloHorarioCancha / horarios_cancha_intervalos | Horario FK CASCADE, día, apertura y cierre propios |
| ExcepcionHorario / horarios_excepciones | Sede PROTECT, cancha opcional PROTECT, tipo, inicio/fin, motivo, creador, anulación y auditoría temporal |

Los horarios se guardan en campos tipados; las horas se interpretan en `America/Lima`.
Una hora de cierre anterior a la apertura cruza al día siguiente; apertura y cierre iguales
se rechazan. Cada cancha hereda el horario de sede por defecto. Puede personalizar días
concretos y conservar la herencia en otros; un día personalizado sin intervalos queda
cerrado. Las horas propias de cancha deben estar dentro del horario semanal de sede.
`Sede.horario_general` queda por compatibilidad con los datos anteriores y no es fuente de
estos horarios.

Las excepciones activas tienen intervalos conscientes de zona horaria y alcance de sede o
cancha. Las anulaciones conservan la fila, actor y fecha. Los cierres de sede afectan sus
canchas. Una ampliación agrega operación durante su intervalo y no elimina los cierres que
la cruzan. La política de prioridad es una propuesta pendiente de confirmación en
DECISIONES.md.

La disponibilidad se calcula en bloques completos de una hora a partir de horarios
semanales y ampliaciones; los bloques que cruzan cierres se devuelven como cerrados y
deshabilitados. También considera inactividad y bloques pasados. La API exige autenticación
y alcance por empresa/sede; no ofrece consulta pública al jugador en esta fase. Incluye
`considera_reservas: false`: todavía no existe motor de reservas ni disponibilidad para
reservar.

## Planes y suscripciones SaaS

| Modelo / tabla | Datos y relaciones |
|---|---|
| PlanSuscripcion / suscripciones_planes | Nombre único sin distinguir mayúsculas, descripción, precio Decimal, moneda, frecuencia, máximos de sedes/empleados/canchas y activo |
| SuscripcionEmpresa / suscripciones_empresas | Empresa 1:1, plan, estado, fechas, importe, moneda, frecuencia acordados |
| PeriodoSuscripcion / suscripciones_periodos | Suscripción, plan, fechas, copia del importe, moneda, periodicidad y creador |
| SolicitudSuscripcion / suscripciones_solicitudes | Empresa, plan, tipo, estado, snapshot de precio/moneda/frecuencia, medio, referencia, solicitante y revisión |
| PagoSuscripcion / suscripciones_pagos | Solicitud 1:1, importe Decimal, moneda, referencia, medio, confirmador y fecha |
| ConfiguracionSuscripcion / suscripciones_configuracion | Días de gracia y último administrador que modificó el valor |

Frecuencias admitidas: mensual, trimestral, semestral y anual. Estados de suscripción:
pendiente, activa, vencida, suspendida y cancelada. El estado vencida se calcula cuando
termina la fecha registrada más los días de gracia; no se reescribe en segundo plano.
Las transiciones y aprobación manual se ejecutan en servicios transaccionales.

Solo puede existir una solicitud pendiente por empresa. Al aprobar, el importe verificado
debe coincidir con el snapshot solicitado; se crea el periodo histórico y, si el importe
es mayor a cero, el PagoSuscripcion independiente. Solicitar o adjuntar una referencia
nunca activa el servicio. Cambiar el precio de un plan no altera periodos previos.

## Reservas y pagos — Fases 4A y 4C

| Modelo / tabla | Datos y relaciones |
|---|---|
| Reserva / reservas | Jugador, cancha, intervalo, duración, total/adelanto `Decimal`, moneda, estado, vencimiento, cotización histórica, clave idempotente |
| BloqueReserva / reservas_bloques | Reserva y cancha, fecha/hora, liberación; PostgreSQL impide cruces activos por cancha |
| HistorialEstadoReserva / reservas_historial_estados | Reserva, estado anterior/nuevo, actor, motivo y fecha |
| MetodoPagoSede / sedes_metodos_pago | Sede, Yape/Plin/transferencia, titular, celular/cuenta/CCI/banco, QR opcional, instrucciones y estado activo |
| PagoReserva / reservas_pagos | Reserva, medio de su sede, tipo (adelanto/total/saldo), importes Decimal solicitado/verificado, estado, referencia, observaciones, idempotencia, revisor, fechas y conciliación |
| HistorialPagoReserva / reservas_historial_pagos | Pago, transición, actor, motivo, datos y fecha; se conserva para auditoría |

El alcance empresarial del pago se deriva de `Reserva → Cancha → Sede → Empresa`; no se
acepta una empresa o sede recibida del cliente como autorización. `PagoReserva` no crea una
relación con `PagoSuscripcion`: los pagos de reserva y las suscripciones del SaaS permanecen
separados. Un índice único parcial limita cada reserva a una solicitud en `pendiente_pago` o
`pendiente_revision`; los servicios y transacciones limitan los pagos aprobados al total
histórico y requieren cubrir el adelanto mínimo antes de pasar a pendiente de confirmación.

Estados de pago: `pendiente_pago`, `pendiente_revision`, `aprobado`, `rechazado`, `vencido` y
`pago_tardio`. Declarar el comprobante no verifica el pago. Los pagos vencidos conservan su
historial; una aprobación que vence antes de la confirmación posterior queda marcada para
conciliación y libera el bloque. `RESERVA_REVISION_PAGO_MINUTOS` es configurable y provisional;
`PAGOS_RESERVA_HABILITADOS` está desactivado por defecto fuera de desarrollo.

maximo_sedes, maximo_empleados y maximo_canchas aceptan null y cero. El código interpreta
null como ausencia de máximo y cero como ningún recurso disponible; confirmar esta
interpretación comercial sigue pendiente. La cuota de canchas se aplica al total de la
empresa conforme al supuesto pendiente indicado en la sección Canchas.

## Restricciones, acceso y migraciones

- Unicidad parcial de RUC no vacío.
- Unicidad de una membresía por usuario, empresa y rol; rol limitado a los valores admitidos.
- RUC opcional y validado como once dígitos cuando se envía.
- Restricciones de coordenadas completas y de rango.
- Unicidad de invitación pendiente por correo y empresa, sin distinguir mayúsculas.
- Una sola solicitud SaaS pendiente por empresa y un solo pago por solicitud.
- Precio Decimal y no negativo; vencimiento de periodo no anterior a inicio.
- Sede, imagen, membresía y solicitud usan PROTECT donde se requiere preservar historial.
- Fase 3A implementa Cancha e ImagenCancha; Fase 3B añade horarios y excepciones.
  Tarifas se agregaron de forma aditiva en Fase 3C, reservas en Fase 4A y pagos manuales de
  reservas en Fase 4C. Caja y kiosco continúan fuera de alcance.

Migraciones nuevas, sin reiniciar ni eliminar datos:

- apps/empresas/migrations/0002_invitacionempleado_registroauditoria_and_more.py
- apps/empresas/migrations/0003_invitacionempleado_sedes_registroauditoria_actor_and_more.py
- apps/sedes/migrations/0001_initial.py
- apps/suscripciones/migrations/0001_initial.py
- apps/suscripciones/migrations/0002_alter_plansuscripcion_nombre_and_more.py
- apps/canchas/migrations/0001_initial.py
- apps/horarios/migrations/0001_initial.py
- apps/reservas/migrations/0001_initial.py y `0002_remove_reserva_reserva_estado_valido_and_more.py`
- apps/pagos/migrations/0001_initial.py

`showmigrations` confirmó las migraciones anteriores aplicadas en la base PostgreSQL
local de desarrollo. No se reinició ni se eliminó esa base. Las pruebas completas usan
otra base PostgreSQL temporal y `makemigrations --check --dry-run` no detectó cambios
faltantes.


## Tarifas — Fase 3C

`ReglaTarifa` (`tarifas_reglas`) pertenece a una `Cancha` mediante una relación protegida.
Una sola estructura representa tarifas `diurna`, `nocturna`, `fin_semana`, `feriado` y
`especial`; almacena días o fechas aplicables, hora inicial/final o día completo, vigencia,
precio por hora `Decimal(10,2)`, moneda PEN, estado activo y usuario creador. Desactivar
preserva el historial.

Las restricciones de base exigen importe mayor a cero, rangos de fecha y hora válidos, tipo
admitido, PEN como moneda y nombre no vacío único dentro de la cancha. La validación de
servicio rechaza reglas activas ambiguas de igual prioridad para periodos superpuestos.
La migración aditiva es `apps/tarifas/migrations/0001_initial.py`; no reinicia, elimina ni
transforma tablas existentes.

## Publicación de calendario — Fase 3D

`Cancha.publicada` es booleano y usa `False` como valor inicial. No agrega una entidad ni
modifica relaciones existentes. Su migración aditiva es
`apps/canchas/migrations/0002_cancha_publicada.py`. Solo una cancha publicada y asociada a
sede y empresa activas se lista públicamente; las canchas inactivas quedan ocultas y las que
están en mantenimiento se muestran sin bloques contratables. La consulta pública serializa
una lista explícita de campos públicos y no reutiliza el serializer administrativo completo.

La disponibilidad conserva `considera_reservas: false`. Las respuestas marcan
`origen=horario_semanal` o `origen=ampliacion_excepcional`; las reglas de precio y la cotización
se calculan con los mismos servicios existentes. Ninguna cotización genera una fila de
reserva o una retención.

## Reservas y bloques de horario — Fase 4A

| Modelo / tabla | Relaciones y datos |
|---|---|
| Reserva / reservas | UUID de idempotencia único por jugador, código público aleatorio, usuario jugador, cancha, inicio/fin conscientes de zona, duración, importe y adelanto Decimal(10,2), moneda PEN, estado, vencimiento y snapshot JSON de la tarifa por bloque. Empresa y sede se obtienen por la cancha para evitar relaciones redundantes. |
| BloqueReserva / reservas_bloques | Reserva, cancha, intervalo de una hora, fecha de creación y liberado_en nullable. Una fila por hora permite reservar varias horas consecutivas y conservar qué intervalo se liberó. |
| HistorialEstadoReserva / reservas_historial_estados | Estado anterior/nuevo, motivo, responsable nullable y fecha. Preserva auditoría sin editar la historia previa. |

La migración aditiva apps/reservas/migrations/0001_initial.py instala primero la extensión
PostgreSQL btree_gist. Una restricción GiST excluye intervalos tstzrange('[)')
superpuestos para la misma cancha cuando liberado_en IS NULL; por eso 19:00–20:00 y
20:00–21:00 son contiguos válidos, pero 19:00–21:00 y 20:00–22:00 no pueden coexistir.
transaction.atomic() bloquea la cancha antes de revisar, calcular y crear sus bloques, y la
restricción de base sigue siendo el último control frente a carreras.

Estados contemplados: retenida, pendiente de pago, pendiente de verificación, confirmada,
vencida, cancelada, rechazada y finalizada. Durante Fase 4A solo se permiten la creación
inicial en retenida y las transiciones retenida → vencida o retenida → cancelada; los
estados de pagos y asistencia quedan inactivos. El servicio que cambia el estado registra
motivo y responsable y no hay un campo de estado escribible por API.

La retención inicial de 15 minutos se configura mediante RESERVA_RETENCION_MINUTOS; es un
valor de desarrollo pendiente de definición comercial. La tarea independiente
expirar_retenciones vence y libera bloques. El endpoint público actualizado declara
considera_reservas: true y oculta datos del jugador; las consultas operativas de 3B
conservan false.
