# Decisiones que requieren aprobación del propietario

Este documento contiene únicamente reglas comerciales o de operación que necesitan una
decisión del propietario. Los valores técnicos indicados son provisionales y **PENDIENTES**;
su presencia en el código no significa que estén aprobados.

## 1. Retención del horario

- **Actual:** el backend reserva temporalmente el bloque y usa
  `RESERVA_RETENCION_MINUTOS=15` como valor configurable.
- **Propuesta PENDIENTE:** mantener 15 minutos, procesar vencimientos cada minuto y permitir
  ajustar la duración por entorno antes de producción.
- **Debe decidirse:** duración comercial y frecuencia operativa del proceso de vencimientos.

## 2. Plazo para verificar el comprobante

- **Actual:** `RESERVA_REVISION_PAGO_MINUTOS=15` es configurable. Declarar el comprobante
  extiende la retención como máximo una vez; un pago aprobado tarde se conserva para
  conciliación, sin recuperar bloques liberados.
- **Propuesta PENDIENTE:** conservar 15 minutos desde la declaración y completar la
  confirmación dentro del mismo plazo.
- **Debe decidirse:** duración final, momento exacto desde el que corre y tratamiento
  operativo de comprobantes recibidos fuera de plazo.

## 3. Ingreso anticipado a la cancha

- **Actual:** el servidor acepta el ingreso solo durante el intervalo reservado
  `[inicio, fin)`. No hay tolerancia anticipada ni posterior.
- **Propuesta PENDIENTE:** habilitar el registro hasta 15 minutos antes del inicio; mantener
  el cierre en la hora final reservada. El valor puede ser cero si se prefiere la regla actual.
- **Debe decidirse:** minutos de anticipación y si se permitirá registrar ingreso después de
  la hora final.

## 4. Cancelación de una reserva confirmada

- **Actual:** el jugador puede cancelar antes del inicio. La cancelación no devuelve
  automáticamente pagos; los pagos aprobados quedan para revisión y se conserva el historial.
  El texto aceptado de la sede queda guardado con su versión.
- **Propuesta PENDIENTE:** mantener esta base, definir con cada sede el plazo de cancelación y
  tramitar cualquier devolución o compensación de forma manual, autorizada y auditada.
- **Debe decidirse:** plazos, reprogramaciones, excepciones comerciales y responsables de
  autorizar compensaciones. Revisar las condiciones con asesoría legal peruana antes de
  producción; considerar errores de cobro, indisponibilidad atribuible a la sede y derechos
  del consumidor.

## 5. Tarifas

- **Actual:** una regla especial tiene prioridad sobre feriado, fin de semana y tarifa por
  rango horario. Un bloque de una hora que cruza dos tarifas usa la regla vigente en su hora
  local de inicio. Cada sede define rangos; no hay una hora universal de corte día/noche.
- **Propuesta PENDIENTE:** conservar la precedencia técnica existente y el precio íntegro por
  bloque; permitir que cada sede configure sus rangos diurnos/nocturnos.
- **Debe decidirse:** prioridad comercial, rangos diurno/nocturno, precio aplicable en
  feriados y fechas especiales, y tratamiento de bloques que crucen medianoche o un cambio de
  tarifa.

## 6. Zona horaria

- **Actual:** el backend usa `America/Lima` para horarios y fechas; `Sede` aún no guarda una
  zona horaria propia.
- **Propuesta PENDIENTE:** mantener una única zona para Perú mientras todas las sedes operen
  allí; añadir zona por sede antes de operar en otras regiones o países.
- **Debe decidirse:** confirmar si el producto se limitará a `America/Lima` o si cada sede
  podrá configurar su zona horaria.
