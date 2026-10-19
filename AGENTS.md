# AGENTS.md — AlToque Pichanga

> **Documento rector para agentes de IA y desarrolladores.** Combina las reglas arquitectónicas del documento original, los requisitos confirmados del negocio y el manual visual aprobado. Debe revisarse antes de diseñar, generar o modificar archivos. Ante una regla de negocio no definida, proponer una alternativa marcada **PENDIENTE**; no presentarla como decisión del dueño del proyecto.

## 1. Identidad, alcance y actores

- **Producto:** AlToque Pichanga, plataforma SaaS de suscripción para empresas dueñas de complejos/canchas de fútbol, con buscador público centralizado, páginas por complejo y paneles de administración.
- **Modelo SaaS real, multiempresa:** distintas empresas se registran, contratan una suscripción a la plataforma y administran sus propios complejos, sedes, canchas, personal y operaciones.
- **Autoridad global:** el **Superadministrador de Plataforma** es la única función con visibilidad administrativa de todas las empresas y sedes. Su consola es independiente de la administración de una empresa.
- **Dueño/Administrador General de Empresa:** gestiona **todas las sedes de SU empresa**, pero nunca las de otras empresas.
- **Administrador de Sede:** administra únicamente las sedes que se le asignen.
- **Cajero/Empleado:** registra operaciones presenciales, valida pagos y QR según permisos, gestiona su turno de caja y ventas del kiosco en sedes asignadas.
- **Cliente/Jugador:** busca canchas, inicia reservas, consulta sus propios pagos/reservas, descarga el QR cuando la reserva ha sido confirmada.
- **Vista pública:** catálogo centralizado de sedes/canchas de múltiples empresas, con búsqueda y filtros de ubicación, fecha, horario, precio y características, más ficha individual por complejo. No revelar datos internos de otras empresas.
- **Producto inicial:** canchas de fútbol; diseñar la lógica para admitir otras disciplinas en el futuro sin ofrecerlas todavía como funcionalidad cerrada.
- **Idioma:** UX y mensajes al usuario en español. Moneda base inicial PEN (S/), horario de 24 h y zona horaria de Perú (`America/Lima`) mientras no se definan múltiples zonas.

## 2. Límites de acceso y aislamiento entre empresas

1. Diseñar aislamiento por empresa en PostgreSQL compartido, mediante relaciones claras con `Empresa` y filtros centralizados por empresa/sede en cada petición, consulta, mutación y evento en tiempo real. No son necesarios esquemas PostgreSQL separados para el MVP.
2. **Nunca** confiar en `empresa_id` o `sede_id` enviados por el navegador como autorización. Resolver el alcance desde la identidad autenticada, su membresía y sus permisos; verificar que cada objeto pertenezca a ese alcance.
3. Los objetos públicos pueden consultarse a través de endpoints deliberadamente públicos, mostrando solo datos destinados al catálogo.
4. Comprobar permisos tanto en la API HTTP como en WebSockets, exportaciones, tareas programadas y operaciones internas. No exponer canales de administración a un jugador.
5. Separar claramente la gestión de suscripciones de plataforma (`Empresa` paga al SaaS) de los cobros por reserva (`Jugador` paga a una sede/empresa).
6. Empleados pueden pertenecer a una o más sedes autorizadas; el dueño de empresa puede revisar únicamente su propia empresa. Las acciones del superadministrador global deben quedar auditadas.
7. Contar con pruebas de acceso cruzado: dos empresas distintas nunca pueden leer ni modificar sedes, reservas, pagos, empleados, caja o datos privados de la otra.

## 3. Reservas: horarios, disponibilidad y estados

- **Unidad de reserva MVP:** intervalos de **una hora**. El jugador puede escoger una o varias horas consecutivas en una misma cancha, si están disponibles.
- **Tarifas:** configurables por cancha, con **tarifa diurna y nocturna** en rangos horarios definidos por la sede. Calcular por bloque cuando una reserva cruza tramos con distintos precios. Guardar desglose y tarifa aplicada en la reserva para conservar el histórico.
- Contemplar horario operativo por día, bloqueos por mantenimiento, cierres extraordinarios y excepciones/feriados; la política de precios especial por feriados queda **PENDIENTE** de aprobación.
- **Sin reservas fijas/recurrentes automáticas en MVP.** Pueden reservarse varios bloques contiguos en una sola operación.
- **Retención temporal del horario:** al iniciar la solicitud, crear una reserva **pendiente de pago** que aparta temporalmente los bloques. El plazo exacto de vencimiento es **PENDIENTE** y debe ser configurable, no una constante enterrada en la lógica.
- Estados orientativos, a refinar en el diseño: `pendiente_pago`, `pendiente_validacion`, `confirmada`, `vencida`, `cancelada`, `rechazada`, `finalizada`. Documentar transiciones válidas; no permitir saltos arbitrarios.
- Expirar y liberar horarios automáticamente, mediante tarea fiable del servidor, al vencer una retención no confirmada. Registrar el cambio y difundir la nueva disponibilidad.
- Evitar abusos: límite de solicitudes pendientes por usuario/dispositivo y rate limiting razonable. La configuración exacta queda por decidir.

### Concurrencia y WebSockets (obligatorio)

- **Frontend:** Vue recibe avisos WebSocket al cambiar disponibilidad (retenida, confirmada, cancelada, liberada). Actualiza el calendario inmediatamente; evita mostrar como libre un bloque que ya fue tomado, en la medida de la latencia de red.
- **Backend en tiempo real:** Django ASGI + Django Channels; Redis como capa de mensajería para las instancias. Usar grupos por cancha y fecha, con información de horarios/estado, **sin datos personales ni montos privados**.
- **La base de datos es la autoridad final:** el WebSocket es informativo y **no reemplaza** la validación de disponibilidad. Al crear o confirmar, usar `transaction.atomic()`, bloqueo concurrente apropiado (`select_for_update` donde corresponda) y restricciones/índices de PostgreSQL para impedir reservas activas superpuestas.
- Modelar intervalos/bloques de forma que no puedan duplicarse para la misma cancha y fecha en estados ocupantes; definir cómo se liberan al vencer/cancelarse. Evitar depender de un `SELECT` previo sin protección transaccional.
- Publicar el evento WebSocket **después** de confirmar la transacción (`transaction.on_commit`). Reconectar y reconsultar la API si se pierde la conexión, se vuelve a enfocar la página o hay incertidumbre.
- **UX si hay carrera real:** cuando dos personas intentan confirmar simultáneamente, solo una obtiene los bloques; la otra recibe una respuesta amable, actualiza calendario y puede elegir otro horario. No se puede prometer cero conflictos de red, sí cero reservas dobles y mensajes claros.
- Probar reservas simultáneas, múltiples horas, vencimiento, liberación, reconexión, dos empresas distintas y pagos aprobados al borde del vencimiento.

## 4. Pagos de reservas, adelantos y confirmación

1. Para separar una cancha se exige **adelanto mínimo del 50%** o pago total. El sistema calcula monto total, adelanto exigido y saldo. No usar números de punto flotante para dinero: `Decimal` y `DecimalField`.
2. **MVP sin pasarela integrada:** mostrar Yape, Plin y/o transferencia **propios de la sede** (datos administrados por su empresa). No centralizar dinero de reservas en la cuenta del SaaS.
3. Generar enlace `wa.me` al WhatsApp oficial de la sede con mensaje previamente redactado (código de reserva, sede, horario y monto) para que el cliente **adjunte manualmente** su captura. Un enlace a WhatsApp no puede adjuntar automáticamente una imagen de comprobante.
4. El mensaje de WhatsApp o la captura **no confirma automáticamente el pago**. Un empleado autorizado verifica el pago recibido y aprueba/rechaza desde el panel. Auditar quién lo hizo y cuándo.
5. No confirmar reservas expiradas ni aprobar un pago que produciría choque de horarios. Crear un flujo de incidencia/conciliación para pagos reportados fuera de plazo.
6. Al aprobar el adelanto, cambiar estado a **confirmada**, registrar monto/método/fecha/validador y saldo pendiente. Enviar correo de confirmación y habilitar ticket QR.
7. Al llegar a la sede, permitir pago presencial del saldo, con desglose por método. Nunca duplicar un pago al registrar también el movimiento de caja.
8. **Pagos con pasarelas, reparto por empresa y comisión por transacción quedan fuera del MVP**, aunque la arquitectura puede añadir adaptadores en el futuro. No deducir que Mercado Pago/Culqi/Niubiz ofrecen una integración específica sin verificar condiciones vigentes.
9. Diferenciar pago de reserva, pago de suscripción SaaS y movimiento de caja. Mantener referencias y relaciones sin mezclar los saldos.

## 5. Cancelaciones y política de no devolución

- **Regla comercial inicial:** la **cancelación voluntaria del jugador no genera devolución del adelanto en la mayoría de los casos**, según condiciones informadas previamente.
- No convertir esto en prohibición absoluta: contemplar derechos del consumidor y legislación peruana vigente, posibles errores de cobro, cobros duplicados, indisponibilidad imputable al complejo y excepciones legales.
- Antes del pago, mostrar condiciones de cancelación/no devolución de la sede y registrar versión/fecha de aceptación. El contenido legal definitivo requiere revisión antes de poner el sistema en producción.
- Reservas canceladas deben liberar horarios según el flujo aprobado y preservar el historial contable.
- Toda devolución excepcional, compensación o cambio de fecha requiere autorización, motivo, importes, registro de auditoría y una regla clara de disponibilidad. **Reprogramaciones, plazos de cancelación y excepciones específicas: PENDIENTE.**
- No ejecutar devoluciones automáticas ni inventar penalidades adicionales en el MVP.

## 6. Suscripciones SaaS (independientes de reservas)

- Cada empresa cliente tiene su cuenta, sedes, administradores y una suscripción propia a AlToque Pichanga.
- Administrar planes, vigencia, renovaciones, estados y comprobación de pago de suscripción desde el **Superadministrador de Plataforma**.
- No asumir precios, periodicidad, pruebas gratis, cantidad máxima de sedes o método de cobro SaaS: **PENDIENTE de definición**. Diseñar campos/relaciones que permitan configurarlos.
- El vencimiento de la suscripción nunca debe eliminar datos ni permitir accesos entre empresas. Proponer una política de acceso restringido/suspensión **PENDIENTE**.
- No cobrar comisión por reserva en MVP. Dejar separación de módulos para futura comisión/pasarela, sin implementarla ahora.

## 7. Kiosco presencial, caja y personal

- El usuario público **puede ver** productos y servicios informativos de la sede (agua, otras bebidas, alquiler de pelotas/chalecos, etc.), pero **no puede comprarlos ni pagarlos online**.
- Los cajeros registran ventas del kiosco **solo presencialmente**, con producto, cantidad, precio, total, método de pago y responsable. Control básico de inventario si se aprueba en el diseño (detallar alcance de stock antes de implementarlo).
- Caja por sede/turno/cajero: apertura, monto inicial, ingresos, egresos autorizados, pagos de saldos en cancha, ventas de kiosco, cierre y conciliación.
- Separar **efectivo físico** de Yape/Plin/transferencias. No sumar por duplicado los adelantos digitales validados previamente al efectivo del turno.
- Mantener trazabilidad de anulaciones, ajustes y diferencias; no borrar movimientos contables sin rastro.
- Facturación electrónica SUNAT queda **FUERA del MVP / PENDIENTE**. No llamarle factura electrónica a un recibo/ticket interno.

## 8. Clientes, autenticación, notificaciones y QR

- Registro/autenticación del jugador mediante **Google OAuth o correo y contraseña**; verificación de correo cuando proceda. No exigir cuenta de WhatsApp, DNI ni SMS para completar el registro MVP.
- El jugador puede revisar **sus** reservas, estados y tickets; el empleado puede revisar reservas únicamente de su sede autorizada.
- **Notificaciones MVP por correo** (solicitud, aprobación, rechazo/caducidad, recordatorio si luego se confirma el alcance). WhatsApp **sin API**: solo enlace `wa.me` con texto prellenado para enviar comprobantes.
- El QR aparece **solo después** de confirmar la reserva. Contiene identificador aleatorio/no predecible o token firmado; **no** incluye DNI, correo, teléfono, datos de pago ni la información personal en texto plano.
- El empleado lo valida mediante una vista móvil autenticada contra el servidor. Verificar empresa/sede, reserva, horario/fecha, estado y si ya fue registrado el ingreso; prevenir reutilización indebida. Registrar fecha y empleado que validó.
- No considerar un QR fotografiado como prueba de pago por sí solo; la API decide su validez.
- Planificar envío asíncrono de correos y reintentos, sin bloquear el flujo principal cuando falle el servidor SMTP.

## 9. Arquitectura y estilo de programación (SOLID)

### Tecnologías acordadas y candidatas
- **Backend:** Python + Django + Django REST Framework, PostgreSQL, ASGI + Channels, Redis para WebSockets.
- **Frontend:** Vue 3 con Composition API y `<script setup>`, Vite, Pinia, Vue Router, Tailwind CSS.
- Bibliotecas de UI, tarea programada/cola (Celery u otra alternativa) y alojamiento: **proponer** antes de agregar dependencias pesadas.
- Evitar sobreingeniería; primero MVP seguro y ampliable.

### Organización modular del backend
- Separar módulos de negocio, por ejemplo: `usuarios`, `empresas`, `suscripciones`, `sedes`, `canchas`, `reservas`, `pagos`, `kiosco`, `caja`, `notificaciones`, `auditoria` y `shared`.
- Mantener carpetas técnicas reconocibles: `models/`, `serializers/`, `repositories/`, `services/`, `views/`, `permissions/`, `tests/` y, cuando corresponda, `consumers/`, `tasks/`, `selectors/`.
- `models`: esquema, constraints y validaciones locales pequeñas. **Modelos/campos/tablas/relaciones de negocio en español** (`Empresa`, `Sede`, `Cancha`, `TarifaHorario`, `Reserva`, `BloqueReserva`, `PagoReserva`, `ProductoKiosco`, `TurnoCaja`, `MovimientoCaja`, etc.); definir explícitamente `db_table` en español y convenciones uniformes.
- `repositories`: acceso al ORM y consultas por alcance; no consultar directamente desde `views`. `services`: casos de uso, reglas de negocio y transacciones. `serializers`: validación/contrato de datos. `views`: HTTP y orquestación delgada.
- `permissions`: control por rol, empresa y sede; también centralizar el alcance en servicios/repositorios para evitar omisiones.
- `shared/`: únicamente elementos verdaderamente comunes (correo, QR, errores, mixins de permisos, helpers de tiempo/dinero), **no** una carpeta de funciones sueltas sin dominio.
- Respetar **SOLID** y DRY: clases y funciones pequeñas, composición e interfaces donde realmente aporten valor, evitar duplicación y condiciones anidadas inmanejables. Los `if` simples y claros **sí están permitidos**; no complicar artificialmente el código solo para eliminarlos.
- Ningún archivo `.py`, `.vue`, `.ts`, `.js` mantenido manualmente puede superar **400 líneas**; objetivo de **200–300 líneas**. Dividir antes de crecer. Excepciones técnicas de archivos autogenerados (migraciones, bundles y lockfiles) deben justificarse, no editarse manualmente.
- Añadir type hints en Python, tipos TypeScript en frontend, validación de entrada, mensajes de error coherentes, logs sanitizados y pruebas de servicios críticos.

### Organización modular del frontend
- Usar `src/modules/` por dominio: `publico`, `autenticacion`, `reservas`, `empresas`, `sedes`, `canchas`, `suscripciones`, `kiosco`, `caja`, `administracion_plataforma`; cada módulo agrupa vistas, `components`, `composables`, `services` y `stores` según necesidad.
- `src/shared/components`: controles base accesibles; `src/shared/composables`: funciones reusables; `src/shared/services`: cliente HTTP/WebSocket y utilidades comunes; `src/shared/styles`: tokens visuales.
- Componentes `.vue` centrados en presentación y eventos; lógica de reservas, validaciones complejas y red separada en composables/stores/services. No extraer cada trivialidad a un archivo solo por dogma.
- Las llamadas HTTP usan un cliente reutilizable, manejo unificado de errores/autenticación y rutas protegidas por rol. Pinia para estados realmente compartidos; no usarlo para cada input local.
- Tailwind CSS y **tokens CSS existentes**, no hexadecimales duplicados en componentes. CSS extra solo para necesidades justificadas (animaciones, estilos globales y tokens). Iconografía consistente tipo Lucide.
- Reutilizar los mismos componentes y temas en landing, directorio público, checkout, SaaS, panel de empresa y consola global.

## 10. Seguridad, calidad y reglas de entrega

- Nunca incluir tokens, claves, credenciales ni teléfonos privados en código fuente, logs o repositorios; usar variables de entorno para secretos.
- Validar datos y permisos en **servidor**; las restricciones de frontend son solo UX.
- Autenticación segura, sesiones y permisos de WebSocket; protección contra abuso, CSRF donde aplique y tratamiento adecuado de datos personales conforme a reglas aplicables.
- Transacciones atómicas en reserva, aprobación de pago, caja e inventario; idempotencia para no registrar dos veces la misma aprobación ni el mismo pago.
- Pruebas obligatorias por módulo: permisos multiempresa; dos intentos simultáneos; bloqueo y vencimiento; cancelación; adelanto/saldo; QR; turno de caja; estados visuales Light y Dark.
- Respetar código legible, sin inventar proveedores de pago, tarifas, políticas legales o datos. Evitar lógica repetida, archivos gigantes y conversiones monetarias inseguras.
- Documentar cambios, decisiones pendientes y supuestos. En cada paso explicar qué se modificó y cómo comprobarlo.

## 11. Modo de trabajo de Antigravity — paso inicial

**No comenzar a programar toda la aplicación ni generar migraciones en el primer paso.** Primero entregar y solicitar validación de:

1. Arquitectura y árbol de carpetas propuestos para backend/frontend, incluyendo WebSockets/ASGI, tareas y módulos compartidos.
2. Esquema de tablas/modelos y relaciones en español con aislamiento por empresa/sede, incluyendo SaaS, caja, pagos, bloques de horarios y auditoría.
3. Roles con matriz simple de permisos y flujos de estados de reserva, pago y suscripción.
4. Estrategia técnica real de prevención de duplicidad y difusión de disponibilidad mediante WebSockets.
5. Decisiones **PENDIENTES** de negocio y los valores que se proponen sin asumir aprobación.

**Detenerse y esperar aprobación del usuario antes de crear código, migraciones o un scaffold del proyecto.**

---

# ANEXO A — Manual visual oficial de AlToque Pichanga

> **Uso:** este anexo forma parte integral de `AGENTS.md` y complementa las reglas de arquitectura, negocio, seguridad y pruebas anteriores. La paleta y las tipografías aquí indicadas son las versiones aprobadas.

## 1. Identidad y objetivo

- Marca: **AlToque** (palabra dominante) y **Pichanga** (debajo, más pequeña).
- Producto: plataforma web peruana para descubrir, comparar y reservar canchas de fútbol.
- Personalidad: deportiva, rápida, urbana, confiable, contemporánea y accesible.
- Estética: negro carbón + verde lima eléctrico + blanco, con superficies sobrias y mucho aire visual.
- Lema opcional en marketing: **«Tu pichanga, al toque.»**
- No modificar ni regenerar el logo oficial. Usar el isotipo, imagotipo y versiones monocromáticas aprobadas.

## 2. Tipografía (opción oficial: Archivo Black + Outfit)

- **Archivo Black**: tipografía de exhibición para títulos principales del hero, titulares de secciones y mensajes promocionales. Tiene un único peso disponible (`400`), que visualmente ya es muy grueso; **no forzar `700` o `800`**. Usarla con moderación en títulos cortos, evitando bloques largos en mayúsculas.
- **Outfit**: tipografía principal de la aplicación para navegación, botones, formularios, calendarios, precios, horarios, fichas de canchas, tablas, panel administrativo, párrafos y encabezados internos densos. Usar pesos `400` (texto), `500` (controles), `600` (subtítulos y botones) y `700` (jerarquías internas).
- **Jerarquía:** `h1` y `h2` de páginas comerciales con Archivo Black; `h3`, `h4` y títulos de tarjetas o dashboard con Outfit `600–700`. Cuando un `h2` sea largo o esté en una vista densa, usar Outfit en lugar de Archivo Black.
- **Marca gráfica:** nunca reconstruir el logotipo «AlToque / Pichanga» con fuentes web; utilizar los archivos aprobados de marca.
- Fallback: `sans-serif`. Cargar desde Google Fonts o usar archivos locales con licencia válida; evitar efectos que simulen negrita en Archivo Black.
- Escritorio: `h1` 48–64 px, `h2` 30–40 px, `h3` 22–28 px, cuerpo 16 px, botones 14–16 px, descripción 14 px.
- Móvil: `h1` 32–40 px, `h2` 26–32 px, cuerpo 16 px; texto auxiliar nunca inferior a 12 px. Adaptar la escala según longitud para impedir desbordamientos.
- Los textos de fechas, precios y horarios deben ser legibles y no llevar inclinación; si hay cifras tabulares usar `font-variant-numeric: tabular-nums`.

## 3. Paleta principal (constante en ambos temas)

| Token | HEX | Uso |
|---|---|---|
| `--brand-lime` | `#C0FA04` | Color identitario, CTA, selección, pequeños acentos |
| `--brand-lime-hover` | `#A9DC00` | Hover de CTA |
| `--brand-lime-pressed` | `#8FBB00` | Estado presionado |
| `--brand-lime-light` | `#F0FBCB` | Resaltado suave en superficies claras |
| `--brand-lime-dark` | `#263710` | Resaltado suave en superficies oscuras |
| `--brand-charcoal` | `#0B0F12` | Identidad oscura, hero y encabezados |
| `--brand-white` | `#FFFFFF` | Blanco de marca |
| `--on-brand-lime` | `#0B0F12` | Texto/iconos **sobre botón lima** |

**Regla de contraste:** el verde `#C0FA04` no se usa como texto pequeño sobre blanco; para enlaces en fondos claros usar `--link` (verde oscuro). Sobre botones lima usar texto negro, nunca blanco.

## 4. Tokens semánticos de los temas

| Token | Claro | Oscuro | Utilidad |
|---|---|---|---|
| `--bg` | `#F6F8FA` | `#0B0F12` | Fondo general de página |
| `--surface` | `#FFFFFF` | `#141B20` | Tarjetas |
| `--surface-2` | `#EEF2F5` | `#1B252C` | Filtros, paneles, secciones secundarias |
| `--surface-3` | `#E6ECEF` | `#26323A` | Hover y panel elevado |
| `--nav-bg` | `#FFFFFF` | `#10161B` | Barra de navegación |
| `--input-bg` | `#FFFFFF` | `#182128` | Inputs y campos de búsqueda |
| `--text` | `#111827` | `#F6F8FA` | Texto principal |
| `--text-muted` | `#526171` | `#A8B4BE` | Descripciones, ubicación, metadatos |
| `--text-subtle` | `#687889` | `#91A0AD` | Leyendas no esenciales |
| `--border` | `#DEE5EB` | `#2D3A44` | Bordes y divisores |
| `--border-strong` | `#BCC8D0` | `#485964` | Bordes con énfasis |
| `--link` | `#4E6800` | `#D8FF7D` | Enlaces legibles por tema |
| `--selection-bg` | `#F0FBCB` | `#263710` | Chip o filtro seleccionado |
| `--hero-bg` | `#0B0F12` | `#10191D` | Hero premium en ambos temas |
| `--hero-text` | `#FFFFFF` | `#FFFFFF` | Titular del hero |
| `--shadow` | `0 8px 28px rgba(11,15,18,.08)` | `0 12px 36px rgba(0,0,0,.28)` | Elevación de tarjetas |

La marca debe lucir bien en ambos modos. En modo claro, la portada puede mantener su **hero oscuro** mientras el buscador, listado y checkout usan fondos claros.

## 5. Colores de estados (no confundirlos con color de marca)

| Estado | Claro texto / fondo | Oscuro texto / fondo |
|---|---|---|
| Disponible / éxito | `#176A4C` / `#E0F7EC` | `#6CE2AF` / `#13392C` |
| Pendiente / advertencia | `#875A00` / `#FFF1CC` | `#FFD77E` / `#3A2B12` |
| Ocupado / error | `#AD3140` / `#FFE8EC` | `#FF8C96` / `#401F28` |
| Información | `#225CA8` / `#E7F0FF` | `#80B8FF` / `#182F4A` |

- Confirmada / pagada: éxito; pendiente de pago: advertencia; sin cupos: error/neutro, siempre con texto explícito.
- Deshabilitado: reducir énfasis, pero conservar etiqueta legible y `disabled` real; no confiar solo en opacidad.
- Los errores de formulario deben presentar mensaje textual asociado al campo. No depender únicamente del color.

## 6. Variables CSS: fuente única de verdad

Copiar este bloque en el CSS global. En Tailwind, mapear estos mismos tokens a clases utilitarias; **no duplicar hexadecimales a mano por componente**.

```css
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Outfit:wght@400;500;600;700&display=swap');

:root {
  color-scheme: light;
  --font-heading: 'Archivo Black', sans-serif;
  --font-body: 'Outfit', sans-serif;

  --brand-lime: #C0FA04;
  --brand-lime-hover: #A9DC00;
  --brand-lime-pressed: #8FBB00;
  --brand-lime-light: #F0FBCB;
  --brand-lime-dark: #263710;
  --brand-charcoal: #0B0F12;
  --brand-white: #FFFFFF;
  --on-brand-lime: #0B0F12;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  /* Valores por defecto: modo claro. */
  --bg: #F6F8FA;
  --surface: #FFFFFF;
  --surface-2: #EEF2F5;
  --surface-3: #E6ECEF;
  --nav-bg: #FFFFFF;
  --input-bg: #FFFFFF;
  --text: #111827;
  --text-muted: #526171;
  --text-subtle: #687889;
  --border: #DEE5EB;
  --border-strong: #BCC8D0;
  --link: #4E6800;
  --selection-bg: #F0FBCB;
  --hero-bg: #0B0F12;
  --hero-text: #FFFFFF;
  --shadow: 0 8px 28px rgba(11, 15, 18, 0.08);
  --success: #176A4C;
  --success-bg: #E0F7EC;
  --warning: #875A00;
  --warning-bg: #FFF1CC;
  --danger: #AD3140;
  --danger-bg: #FFE8EC;
  --info: #225CA8;
  --info-bg: #E7F0FF;
}

html[data-theme='dark'] {
  color-scheme: dark;
  --bg: #0B0F12;
  --surface: #141B20;
  --surface-2: #1B252C;
  --surface-3: #26323A;
  --nav-bg: #10161B;
  --input-bg: #182128;
  --text: #F6F8FA;
  --text-muted: #A8B4BE;
  --text-subtle: #91A0AD;
  --border: #2D3A44;
  --border-strong: #485964;
  --link: #D8FF7D;
  --selection-bg: #263710;
  --hero-bg: #10191D;
  --hero-text: #FFFFFF;
  --shadow: 0 12px 36px rgba(0, 0, 0, 0.28);
  --success: #6CE2AF;
  --success-bg: #13392C;
  --warning: #FFD77E;
  --warning-bg: #3A2B12;
  --danger: #FF8C96;
  --danger-bg: #401F28;
  --info: #80B8FF;
  --info-bg: #182F4A;
}

html, body { min-height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.5;
}
/* Archivo Black ya es muy gruesa: su peso real es 400. */
h1, h2 {
  font-family: var(--font-heading);
  font-weight: 400;
  line-height: 1.1;
  overflow-wrap: break-word;
}
/* La interfaz y los encabezados densos priorizan legibilidad. */
h3, h4 {
  font-family: var(--font-body);
  font-weight: 700;
  line-height: 1.25;
}
a { color: var(--link); }
:focus-visible {
  outline: 3px solid var(--brand-lime);
  outline-offset: 3px;
}

.btn-primary {
  background: var(--brand-lime);
  color: var(--on-brand-lime);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font: 700 15px var(--font-body);
  min-height: 44px;
  padding: 0 20px;
  cursor: pointer;
}
.btn-primary:hover { background: var(--brand-lime-hover); }
.btn-primary:active { background: var(--brand-lime-pressed); }
.btn-primary:disabled { opacity: .55; cursor: not-allowed; }

.card {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}
.input-field {
  background: var(--input-bg);
  color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  min-height: 44px;
}
.input-field::placeholder { color: var(--text-muted); }
```

## 7. Reglas obligatorias de componentes

1. **Navbar:** usar `--nav-bg`, `--text`, `--border`. Logo adecuado al fondo. Acciones principales con lima.
2. **Hero:** fondo oscuro en claro y oscuro; título blanco con palabras clave lima. Botón primario lima/negro. Evitar imagen que compita con el título.
3. **Buscador:** campo de ubicación, fecha, hora, tipo de cancha y CTA muy claros. Inputs con fondo `--input-bg` y bordes visibles.
4. **Tarjetas de cancha:** foto de cancha real, nombre, distrito, características, precio `S/` por hora y CTA Reservar; respetar el mismo espaciado en ambos modos.
5. **Calendario:** mostrar día, horario y zona horaria de forma inequívoca; disponibles, ocupados, seleccionados y bloqueados deben diferenciarse por **color más etiqueta o icono**, no solo color.
6. **Reservas y checkout:** legibilidad antes que dramatismo; resumen de fecha, hora, precio y estado visible; confirmación diferenciada del paso previo.
7. **Filtros:** chips no seleccionados usan `--surface-2`; seleccionados `--selection-bg`, borde lima y texto según tema.
8. **Panel administrativo:** priorizar densidad controlada, tablas claras, cabeceras visibles, estados semánticos y filtros consistentes.
9. **Iconos:** estilo Lucide, grosor uniforme de 1.75–2 px. No mezclar sistemas de iconos arbitrariamente.
10. **Bordes y radio:** 12 px para botones/inputs; 16 px para cards; 24 px para modales/paneles grandes.

## 8. Modo claro / oscuro

- Exponer un selector de tema con: **Claro / Oscuro / Sistema**.
- En “Sistema”, seguir `prefers-color-scheme`; si el usuario fija un tema, persistirlo localmente.
- Aplicar el tema mediante `data-theme='light'` o `data-theme='dark'` en `<html>`.
- Cambiar todos los componentes mediante tokens, incluyendo overlays, modales, calendarios, datepickers, tooltips, gráficos y menús.
- Evitar destellos de tema incorrecto al cargar la aplicación (inicializar el atributo lo antes posible).
- Verificar contraste WCAG AA: 4.5:1 para texto normal y 3:1 para texto grande, íconos funcionales y controles relevantes.
- El logo a todo color está diseñado para fondo oscuro. En superficie clara, usar su versión negra o una presentación sobre bloque carbón para conservar contraste.

## 9. Distribución y responsive

- Máximo de contenido recomendado: 1200–1280 px, centrado.
- Espaciado de layout: escala de 4/8/12/16/24/32/48/64 px.
- Desktop: tarjetas de cancha de 3 columnas si el ancho lo permite; tablet 2; móvil 1.
- Pantallas de reserva: filtros accesibles, resumen visible y CTA principal fácil de pulsar, altura mínima 44 px.
- No ocultar información necesaria (precio final, disponibilidad, fecha) por motivos estéticos.
- Precios peruanos en `S/`, formato coherente, y horarios en convención clara de 24 horas.

## 10. Casos de prueba visual obligatorios

Antes de dar por terminada una funcionalidad, comprobar en **claro y oscuro**, tanto móvil como escritorio: landing, buscador, resultados, detalle de cancha, selección de horario, checkout, perfil, historial y panel administrativo. Comprobar texto largo, estados vacíos, errores, loading, foco de teclado y controles deshabilitados.

### Regla final para el agente

**No improvisar una nueva paleta, tipografía o sistema de espaciado por página.** Reutilizar los tokens anteriores. Cuando una nueva interfaz necesite un color, mapearlo a su función semántica en ambos temas antes de usarlo. Mantener el logo “AlToque” dominante y “Pichanga” secundario conforme a los recursos de marca proporcionados.

## 12. Datos demo reproducibles para vistas autenticadas

- Los datos locales de demostración se crean únicamente con el comando Django `generar_datos_demo`, en PostgreSQL de loopback, con `DEBUG=True` y la variable explícita `ALTOQUE_PERMITIR_DATOS_DEMO=1`. El comando debe detenerse antes de escribir si alguna condición no se cumple.
- Las cuentas de ejemplo usan `@example.test`, pasan por el flujo normal de inicio de sesión y conservan sus roles reales. Las pruebas no deben saltarse autenticación o permisos para probar paneles y APIs.
- Toda entidad demo con campo de nombre o descripción debe incluir la marca `[DEMO ALTOQUE]` y un identificador estable. Los registros auxiliares sin esos campos se identifican únicamente mediante su relación con una entidad demo marcada. El comando solo puede actualizar registros identificados como suyos; ante una colisión no marcada debe abortar y dejar la transacción intacta.
- Las contraseñas se generan aleatoriamente, no se muestran en terminal ni se guardan en el repositorio. `docs/USUARIOS_PRUEBA_LOCAL.md` es local e ignorado por Git; ejecuciones repetidas leen ese archivo y mantienen las mismas contraseñas.
- El seeder es idempotente y transaccional. Mantener separados los datos de demostración de los datos reales y no crear reservas, pagos o movimientos contables para poblar vistas de horarios.
