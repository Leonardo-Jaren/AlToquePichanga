# Usuarios de prueba — Fases 3B, 3C, 3D, 4A y 4B

Este fixture sirve para recorrer horarios, tarifas, calendario, retenciones y disponibilidad en tiempo real con siete cuentas ficticias locales. Todas las cuentas usan el inicio de sesión normal de la aplicación (`/ingresar`, correo y contraseña); el comando no agrega rutas especiales ni omite permisos. La consulta pública está disponible en `/canchas-publicas` y no necesita sesión; solicitar o consultar reservas sí requiere iniciar sesión.

## Crear los datos

Desde PowerShell, ejecuta en el backend después de instalar dependencias y aplicar las migraciones:

```powershell
cd "D:\Descargas google\AlToquePichanga\backend"
python manage.py migrate
$env:ALTOQUE_PERMITIR_DATOS_DEMO = "1"
python manage.py generar_datos_demo
Remove-Item Env:ALTOQUE_PERMITIR_DATOS_DEMO
```

El comando solo funciona con `DEBUG=True`, PostgreSQL y `localhost`, `127.0.0.1` o `::1`. Si una condición falla, detiene la ejecución. No uses el opt-in en producción. Las contraseñas se guardan únicamente en `docs/USUARIOS_PRUEBA_LOCAL.md`, ignorado por Git; el comando no las imprime ni las cambia si ya coinciden. Si el archivo ya existe con contenido ajeno al formato del seeder, no lo sobrescribe. La guía generada antigua de Fase 3D se actualiza conservando el bloque JSON local.

## Cuentas

| Correo | Rol | Alcance esperado |
|---|---|---|
| `demo-superadmin@example.test` | Superadministrador de plataforma | Lectura global y administración global según permisos reales. |
| `demo-dueno-a@example.test` | Dueño de empresa A | Ambas sedes de la empresa A; sin acceso a B. |
| `demo-dueno-b@example.test` | Dueño de empresa B | Ambas sedes de la empresa B; sin acceso a A. |
| `demo-admin-sede-a@example.test` | Administrador de sede | Solo la sede A Centro asignada. |
| `demo-cajero-a@example.test` | Cajero | Lectura en A Centro; no puede modificar horarios. |
| `demo-jugador@example.test` | Jugador | Sin membresías de empresa. |
| `demo-jugador-b@example.test` | Jugador | Sin membresías de empresa; cuenta independiente para probar sesiones simultáneas. |

Consulta las contraseñas locales en `docs/USUARIOS_PRUEBA_LOCAL.md` y entra por `/ingresar`.

## Escenario de horarios y tarifas

El fixture crea dos empresas independientes, dos sedes por empresa y seis canchas. Cada sede tiene horario semanal. En A Centro hay una cancha que hereda el horario completo de la sede y otra con horario propio de lunes a viernes que hereda sábado y domingo. A Centro tiene una ampliación especial futura a nivel de sede y la cancha con horario propio tiene un cierre futuro por mantenimiento. Las excepciones incluyen el motivo marcado como demo.

Las entidades del fixture incluyen `[DEMO ALTOQUE]` y una marca estable. El comando es transaccional, repetible y aborta ante una colisión no marcada; no elimina cuentas ni datos ajenos. Las fechas de ampliación y mantenimiento se actualizan a la próxima fecha correspondiente al repetir la generación.

El fixture incorpora 22 reglas de precio de ejemplo en las dos empresas. Incluye reglas
diurnas, nocturnas, de fin de semana, feriados y fechas especiales, además de canchas con
horarios operativos cerrados y consultas de varias horas. Estos precios son datos locales
demostrativos; no son valores comerciales aprobados.

## Comprobaciones manuales

1. Inicia sesión por `/ingresar` con cada cuenta y verifica que su panel muestre su rol.
2. Como dueño A, confirma que no puedes consultar datos de B; repite como dueño B.
3. Como administrador y cajero, verifica que solo se muestre A Centro; intenta cambiar un horario como cajero y confirma que la API lo deniega.
4. Como superadministrador, consulta empresas, sedes y canchas de A y B.
5. Como jugador, confirma que no aparece ninguna membresía ni panel de empresa.
6. Abre la cancha heredada, la cancha con horario propio y sus excepciones para revisar la diferencia entre horario de sede, horario de cancha y cierres/ampliaciones.

7. Como dueño de Empresa A, selecciona A Centro y abre **Tarifas**. Elige una cancha con reglas para consultar, editar o desactivar; el administrador de sede solo ve A Centro.
8. En **Precios por horario**, consulta una fecha y calcula varias horas consecutivas. Los bloques cerrados no muestran precio; los que no tienen regla activa indican que falta configurar una tarifa.
9. Como cajero de A Centro, abre **Consultar tarifas**. Puede consultar reglas y calcular, pero no crear, editar ni cambiar su estado.
10. Como superadministrador, consulta tarifas de ambas empresas; como dueño A o B confirma que no puede consultar ni editar las canchas de la otra empresa. El jugador no tiene estos endpoints administrativos.

## Comprobaciones de calendario — Fase 3D

Las rutas exactas de los paneles son:

| Rol | Ruta | Qué comprobar |
|---|---|---|
| Dueño de Empresa A | `/panel/dueno` → **Calendario** | Elige A Centro o A Norte y una cancha. Cambia entre Día y Semana y revisa precios y cierres. |
| Administrador de sede | `/panel/administrador_sede` → A Centro → **Calendario** | Solo aparecen las canchas de A Centro; puede publicar una cancha desde **Canchas** si corresponde. |
| Cajero | `/panel/cajero` → **Calendario** | Consulta precios y cierres sin poder modificar publicación, horarios o tarifas. |
| Superadministrador | `/panel/plataforma` → **Calendario** | Consulta globalmente las sedes y canchas de ambas empresas. |
| Jugador / vista pública | `/canchas-publicas` | Ve solo las canchas que su empresa publicó y elige una fecha para consultar horarios y precios. |

Inicia sesión por `/ingresar` con el correo de la cuenta correspondiente y usa la contraseña
local de `docs/USUARIOS_PRUEBA_LOCAL.md`. El usuario jugador no tiene acceso a administración;
la página pública también puede probarse sin iniciar sesión.

### Escenarios

1. En **Calendario**, cambia de día a semana y usa los controles de fecha anterior/siguiente.
2. Abre **Ver detalles** en un bloque para revisar el estado, la tarifa y si procede de una
   ampliación excepcional.
3. Selecciona dos bloques consecutivos con tarifa y pulsa **Cotizar selección**. El total lo
   devuelve Django. Un bloque cerrado, sin tarifa o no consecutivo no puede añadirse a la
   cotización. Esta simulación no crea ni bloquea una reserva.
4. El seeder local publica `[DEMO ALTOQUE] Cancha A heredada` y
   `[DEMO ALTOQUE] Cancha B Centro 1`. La publicación se puede revisar o cambiar en el
   formulario administrativo de **Canchas**; queda desactivada por defecto en canchas nuevas.
5. Para comprobar aislamiento, inicia como dueño A y abre A Centro/A Norte; luego entra como
   dueño B y abre B Centro/B Sur. La ruta pública puede listar las dos empresas solo porque
   cada cancha del fixture indicado está publicada; las APIs administrativas mantienen su
   alcance independiente.
6. Los bloques pasados, cierres y mantenimiento no muestran precio contratable. La interfaz
   incorpora retenciones vigentes y aclara que todavía no hay pago ni confirmación.

`docs/USUARIOS_PRUEBA_LOCAL.md` sigue ignorado por Git y conserva contraseñas estables
generadas por el seeder. El comando lo actualiza de forma idempotente; no copies credenciales
reales a este documento versionado.

## Comprobaciones de reservas — Fase 4A

Antes de explorar, ejecuta `generar_datos_demo` con el opt-in descrito arriba. Las tres
reservas ficticias usan claves idempotentes estables, el usuario jugador y canchas marcadas:

| Cuenta / empresa | Cancha y horario (próximo lunes) | Resultado esperado |
|---|---|---|
| Jugador / Empresa A | `[DEMO ALTOQUE] Cancha A heredada`, 18:00–19:00 | Retención temporal activa durante el plazo provisional. |
| Jugador / Empresa A | La misma cancha, 19:00–20:00 | Libre, contiguo a la retención. |
| Jugador / Empresa A | La misma cancha, 21:00–22:00 | Retención vencida; bloque liberado e historial conservado. |
| Jugador / Empresa B | `[DEMO ALTOQUE] Cancha B Centro 1`, 19:00–21:00 | Retención de dos horas en otra empresa. |

El seeder nunca crea dos reservas activas incompatibles. Los conflictos de horarios que se
solapan parcialmente se prueban con dos usuarios y PostgreSQL. El plazo inicial es 15 minutos
solo para desarrollo; ejecutar el seeder de nuevo no reabre retenciones vencidas o canceladas.

1. Inicia sesión como `demo-jugador@example.test` y abre `/canchas-publicas`.
2. Selecciona el próximo lunes, la cancha A publicada y un bloque libre consecutivo. Revisa
   el total y el adelanto mínimo del 50%; solicitar la retención muestra código, estado y
   vencimiento, sin registrar un pago.
3. Abre `/mis-reservas` para consultar detalle o cancelar una retención propia.
4. Comprueba el bloque A 18:00 como retenido. Las pruebas de API/concurrencia verifican que
   una solicitud superpuesta responde con conflicto y refresca disponibilidad.
5. Como dueño A o administrador A, abre **Calendario** y **Reservas**: solo verás sedes de tu
   alcance. Repite como dueño B y confirma que no ve datos de A.
6. Ejecuta `python manage.py expirar_retenciones` para vencer retenciones cuyo plazo terminó;
   en operación debe programarse en el servidor, por ejemplo cada minuto.
7. En **Reservas** revisa filtros, tabla y detalle. Las consultas del superadministrador son
   globales y quedan auditadas.

Las retenciones no crean pagos y no equivalen a reservas confirmadas. Fase 4A no genera
comprobantes, QR ni movimientos de caja.

## Disponibilidad entre dos navegadores — Fase 4B

La vista pública es `/canchas-publicas` y funciona con jugadores o sin iniciar sesión. La
matriz administrativa se encuentra en **Calendario** de `/panel/dueno`,
`/panel/administrador_sede`, `/panel/cajero` y `/panel/plataforma`; cada panel solo recibe las
canchas de su alcance autorizado. Ambas vistas consultan REST al cambiar la disponibilidad.

Con PostgreSQL local encendido, inicia estos procesos en dos terminales (usa el `.env` local
de desarrollo; `USE_REDIS_CHANNEL_LAYER=False` permite InMemory en un solo proceso):

```powershell
# Terminal 1 — backend
cd "D:\Descargas google\AlToquePichanga\backend"
python manage.py runserver 127.0.0.1:8000
```

```powershell
# Terminal 2 — frontend
cd "D:\Descargas google\AlToquePichanga\frontend"
npm run dev -- --host localhost --port 5173 --strictPort
```

El generador conserva las contraseñas locales existentes. Abre dos perfiles independientes
(por ejemplo Chrome normal y Edge, o Chrome normal e incógnito) para usar cookies separadas:

1. En ambos perfiles entra a `http://localhost:5173/ingresar`.
2. En Chrome inicia como `demo-jugador@example.test`; en Edge como
   `demo-jugador-b@example.test`. Las contraseñas están en el archivo local ignorado
   `docs/USUARIOS_PRUEBA_LOCAL.md`; no se guardan en este documento versionado.
3. En ambos abre `http://localhost:5173/canchas-publicas`, selecciona `[DEMO ALTOQUE] Cancha A heredada` y la misma fecha futura. Un visitante también puede consultar la disponibilidad sin sesión.
4. En A selecciona 19:00–20:00 y solicita la retención. En B el bloque debe pasar a ocupado
   automáticamente, sin recargar. Si B ya lo tenía seleccionado, la interfaz invalida esa
   selección y muestra un aviso para elegir otro horario.
5. Cancela desde `/mis-reservas` en A. B debe ver el horario disponible después de la consulta
   REST disparada por el evento.
6. Para probar vencimiento, crea otra retención y ejecuta en un proceso backend
   `python manage.py expirar_retenciones --continuo --intervalo 60`. El valor configurable
   actual es 15 minutos y sigue pendiente de aprobación comercial. Espera el vencimiento para
   comprobar la liberación en B; detén el proceso con Ctrl+C.
7. En DevTools → **Network** → **WS**, bloquea y restablece la red. La conexión reintenta de
   forma limitada y reconsulta REST al reconectar. También puedes usar **Actualizar
   disponibilidad** si el socket no se recupera.
8. Para probar aislamiento, inicia como administrador A y solicita una cancha privada de B:
   el servidor debe rechazarla. Jugadores y visitantes solo pueden suscribirse a canchas
   publicadas; un administrador queda limitado a las sedes que tiene asignadas.

Sin usuarios también se puede verificar el flujo de solo lectura: abre un tercer perfil sin
iniciar sesión en `/canchas-publicas`; recibirá los cambios de una cancha publicada, pero no
podrá solicitar la retención. Así se comprueba la suscripción pública anónima sin crear una
cuenta.

La E2E ejecuta el escenario de dos jugadores con contextos Chromium independientes mediante
`npm run test:e2e`; prepara el demo bajo las guardas locales y usa puertos aislados 18200/15173.
No la ejecutes contra producción.

## Pagos manuales — Fase 4C

El generador idempotente conserva las cuentas anteriores y agrega métodos/pagos de prueba en
las cuatro sedes demo. Para actualizar la base local, aplica migraciones y ejecuta el seeder
protegido (no imprime ni cambia contraseñas que sigan siendo válidas):

```powershell
cd "D:\Descargas google\AlToquePichanga\backend"
python manage.py migrate
$env:ALTOQUE_PERMITIR_DATOS_DEMO = "1"
python manage.py generar_datos_demo
Remove-Item Env:ALTOQUE_PERMITIR_DATOS_DEMO
```

Las claves continúan en `docs/USUARIOS_PRUEBA_LOCAL.md`, que está ignorado por Git. Todos los
medios de pago, números y referencias del seeder son ficticios (ceros); no realices pagos ni
uses sus enlaces como contactos reales.

1. En un perfil inicia como `demo-jugador@example.test`; crea una retención en
   `/canchas-publicas` o abre **Pago** desde `/mis-reservas`. Elige **Adelanto mínimo** o
   **Pago total** y confirma que el importe sale del snapshot histórico.
2. Consulta los datos del medio y el mensaje de WhatsApp. En los datos demo, inspecciona el
   destino `wa.me/00000000000` sin abrirlo. El mensaje no adjunta la captura: en una sede real,
   el jugador la adjunta manualmente.
3. Registra una referencia ficticia y pulsa **Ya envié mi comprobante**. La vista debe quedar
   en **Comprobante por revisar**; abrir WhatsApp o declarar el envío nunca equivale a aprobar.
4. En otro perfil independiente entra como `demo-cajero-a@example.test`, abre
   `/panel/cajero` → **Pagos**, busca el código de reserva y abre **Revisar**. Comprueba el
   importe y el movimiento fuera del sistema antes de aprobar o rechazar. En local usa solo
   referencias ficticias.
5. Después de aprobar, el pago queda verificado y la reserva en `pendiente_confirmacion`.
   No aparecerá QR ni correo hasta la Fase 4D. Si vence el plazo de revisión, el horario se
   libera y un pago ya aprobado queda marcado para conciliación.
6. Como dueño A (`/panel/dueno`) o administrador asignado
   (`/panel/administrador_sede`), abre **Pagos** y usa **Configurar Yape**, **Configurar Plin**
   o **Configurar Transferencia**. El formulario se abre en un modal con cancelar y guardar.
   El cajero solo consulta/revisa y no puede cambiar cuentas; otros dueños no ven estos datos.

Para repetir todo el flujo, usa una nueva hora libre en el calendario. El plazo técnico
`RESERVA_REVISION_PAGO_MINUTOS=15` es provisional, configurable y pendiente de aprobación;
los pagos están apagados por defecto cuando `DEBUG=False`. La E2E automatiza jugador + cajero
con contextos Chromium independientes en claro móvil y oscuro escritorio mediante
`npm run test:e2e -- e2e/pagos-manuales.spec.js`. El test verifica el `href` de WhatsApp sin
abrirlo, no envía mensajes ni usa servicios externos.
