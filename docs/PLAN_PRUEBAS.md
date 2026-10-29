# Plan y resultados de pruebas — Fases 0, 1, 2, 3A–3D y 4A

Actualizado: 24 de octubre de 2026 (America/Lima).

## Verificación histórica completa — Fase 3A

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 69 aprobadas, 0 fallidas (86,16 s) |
| Frontend Vitest | 70 aprobadas, 0 fallidas (18,38 s) |
| Total automatizado | 139 aprobadas, 0 fallidas, 0 omitidas |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff | Sin errores |
| Vite build | Compilación correcta (11,04 s) |

Estos resultados son de la ejecución final local para Fase 3A. Incluyen toda la cobertura
anterior y las pruebas nuevas de canchas. No equivalen a una ejecución remota de GitHub
Actions.

## Última verificación completa — Fase 3B

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 90 aprobadas, 0 fallidas (178,73 s) |
| Frontend Vitest | 79 aprobadas, 0 fallidas (10,11 s) |
| Total automatizado | 169 aprobadas, 0 fallidas, 0 omitidas |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff | Sin errores |
| Vite build | Compilación correcta (7,68 s de compilador) |

La suite de backend se ejecutó en serie con una carpeta temporal nueva porque Windows
denegó lectura sobre el directorio temporal predeterminado de pytest. Las cuatro advertencias
restantes corresponden a pruebas que sustituyen la configuración de base de datos al revisar
las guardas del comando demo. No equivalen a fallos ni a una ejecución remota de CI.

## Comandos de la verificación final

Desde backend:

    .\venv\Scripts\python.exe -m pytest tests -q
    .\venv\Scripts\python.exe manage.py check
    .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
    .\venv\Scripts\ruff.exe check .

Desde frontend:

    npm run test:run
    npm run build

En Fase 3B, pytest usó una ruta nueva con `--basetemp` para aislar la suite del directorio
temporal bloqueado de Windows. Si aparece el mismo error, usa una ruta temporal local nueva.

pytest-django usa PostgreSQL temporal para integración y concurrencia. No se usa SQLite.
No se midió por separado la duración de `check`, migraciones ni Ruff.

## Pruebas enfocadas durante la implementación

Se limitaron a los módulos afectados hasta que el código quedó estable:

Backend:

    .\venv\Scripts\python.exe -m pytest tests/test_fase3a_canchas.py -q

Resultado final focalizado: 9 aprobadas en 20,50 s. El caso PostgreSQL concurrente de
`test_fase3a_concurrencia.py` también aprobó en la ronda enfocada anterior y volvió a pasar
en la suite completa.

Frontend:

    npm run test:run -- tests/Fase3A.test.js

Resultado final focalizado: 17 aprobadas en 1,94 s. La verificación completa de arriba se
ejecutó una vez después de las correcciones; no se repitieron suites completas durante los
cambios incrementales.

Fase 3B:

- Backend `tests/test_fase3b_horarios.py`: 10 aprobadas en 19,29 s.
- Backend `tests/test_usuarios_prueba.py`: 11 aprobadas en 72,01 s.
- Frontend `tests/Fase3B.test.js`: 9 aprobadas.
- La cobertura completa de estos módulos también está incluida en la verificación final
  de 90 pruebas backend y 79 frontend.

Cobertura backend: altas, detalle, edición y validaciones; relación única con la sede;
acceso de dueño, administrador asignado, cajero en solo lectura y superadministrador;
aislamiento entre empresas y sedes; filtros y paginación; estados y reactivación; cupo SaaS
por empresa y dos altas/reactivaciones simultáneas al último cupo en PostgreSQL; imágenes
válidas e inválidas por firma, extensión y tamaño; retiro lógico y auditoría.

Cobertura frontend: listado y filtros; alta y edición; validaciones y errores API; cambio de
estado y confirmación; acciones según rol; carga/vacío/error; galería; y tokens en Claro y
Oscuro.

## Resultado histórico de Fase 2

Backend: 59 aprobadas; frontend: 53 aprobadas; total: 112 aprobadas, 0 fallidas y 0
omitidas. Las 85 pruebas de Fase 1 (45 backend y 40 frontend) se conservaron dentro de esas
ejecuciones. Esos conteos son históricos y no sustituyen los resultados finales de Fase 3B.

## Cobertura registrada en Fase 2

Backend: registro pendiente de empresa, varias empresas por dueño, varios dueños,
búsqueda/paginación global y estados autorizados; aislamiento de sedes y prevención
de transferencias; asignación de sedes, revocación y último dueño; token de invitación
hash, vencimiento, aceptación y uso único; creación de planes, revisión manual, rechazo
de importe incorrecto, suscripción, renovación y precio histórico; gracia configurada;
vigencia efectiva; separación de PagoSuscripcion; y límites simultáneos de sedes y empleados
con dos transacciones PostgreSQL concurrentes.

Frontend: paginación y selección persistida de empresa, estados de error/carga, búsqueda
administrativa, edición de empresa, validación del servidor, vacío y creación de sedes,
restricciones de rol, asignación de sedes, estado e historial de suscripción, configuración
de planes, precisión decimal sin Number, tokens semánticos para Claro/Oscuro y etiquetas.

La suite de Fase 1 mantiene cobertura de login, CSRF, perfiles, Google simulado, permisos,
restablecimiento y verificación de correo. Las pruebas de Fase 0 mantienen salud de API y
selector Claro/Oscuro/Sistema.

## Integración continua

.github/workflows/ci.yml ejecuta Ruff, manage.py check, comprobación de migraciones,
pytest tests contra PostgreSQL 17, Vitest con npm ci y compilación de producción. El
workflow contiene las nuevas pruebas porque ejecuta la suite completa. La ejecución
remota todavía está pendiente.

## Validaciones externas pendientes

- Google OAuth real: faltan credenciales y prueba con cuenta autorizada.
- SMTP real: falta entrega a una bandeja real y configuración del worker.
- GitHub Actions remoto: no se afirma que haya pasado.
- No se probaron pagos ni reservas porque siguen fuera del alcance de Fase 3B.
- La cobertura de canchas se ejecutó y aprobó en la verificación histórica de Fase 3A.

La suite no sustituye una revisión de despliegue, configuración de secretos o interfaz
en dispositivos físicos. Las pantallas nuevas tienen pruebas de componentes y compilación.


## Fase 3C — Verificación final (19 de octubre de 2026)

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 99 aprobadas, 0 fallidas (180,13 s) |
| Frontend Vitest | 90 aprobadas, 0 fallidas (4,44 s) |
| Total automatizado | 189 aprobadas, 0 fallidas, 0 omitidas |
| Django check | Sin incidencias (1,52 s) |
| makemigrations --check --dry-run | Sin cambios pendientes (1,59 s) |
| Ruff | Sin errores (0,03 s) |
| Vite build | Compilación correcta (1,46 s) |
| Migración `tarifas.0001_initial` | Aplicada a la base local de desarrollo (1,77 s) |

El backend se ejecutó con `--basetemp .pytest-f3c-full-20261019`, separado del temporal
bloqueado de Windows. Las cuatro advertencias fueron de pruebas que sustituyen la
configuración de `DATABASES` para comprobar las restricciones del seeder; no hubo fallos.

Pruebas enfocadas:

- Backend `tests/test_fase3c_tarifas.py`: 8 aprobadas en 19,10 s.
- Backend `tests/test_usuarios_prueba.py -k "creacion_idempotente or fixture_de_tarifas"`:
  2 aprobadas en 33,69 s.
- Frontend `Fase3C.test.js`, `AutenticacionStore.test.js`, `ClienteApi.test.js`,
  `ManejoSesion.test.js` y `Proteccion.test.js`: 30 aprobadas en 3,78 s.

La suite completa mantiene las pruebas de Fase 3B y añade cobertura de tarifas, aislamiento
multiempresa, reglas ambiguas, importes Decimal, horas consecutivas, cierres y precios
faltantes. La regresión de autenticación verifica sesión vencida (401), acceso denegado
(403), restauración tras recarga, cambio de usuario, cierre y limpieza del estado de empresa.

`showmigrations tarifas` confirmó `[X] 0001_initial`. El generador local terminó sin
sobrescribir las credenciales ignoradas por Git y dejó 6 cuentas, 2 empresas, 4 sedes,
6 canchas y 22 tarifas demostrativas. Los importes del fixture no son precios comerciales.
`considera_reservas: false` se mantiene; no se probaron ni implementaron reservas o pagos.

La compilación y las pruebas son locales. No se afirma que GitHub Actions remoto haya pasado.

## Fase 3D — Verificación final (19 de octubre de 2026)

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 104 aprobadas, 0 fallidas (184,29 s) |
| Frontend Vitest | 97 aprobadas, 0 fallidas (14,91 s) |
| Total automatizado | 201 aprobadas, 0 fallidas |
| Django check | Sin incidencias (1,94 s) |
| makemigrations --check --dry-run | Sin cambios pendientes (2,15 s) |
| Ruff | Sin errores (1,26 s) |
| Vite build | Compilación correcta (9,14 s) |
| Migraciones | `canchas.0002_cancha_publicada` y `tarifas.0001_initial` aplicadas |

Las 169 pruebas reportadas al cierre de Fase 3B y las 189 pruebas de Fase 3C continúan
incluidas en las suites. pytest usó `--basetemp .pytest-f3d-final-20261019`; no se cambió
la base local para crear la base temporal. Las cuatro advertencias provienen de pruebas del
seeder que sustituyen `DATABASES` para verificar sus guardas; no hubo fallos.

La regresión de cotización pública incluye una sesión válida sin token CSRF: las vistas
deliberadamente públicas no usan autenticación de sesión y la cotización de solo lectura
funciona sin crear una reserva. Prueba enfocada: 1 aprobada (4 pruebas hermanas deseleccionadas,
4,05 s). La verificación manual en `/canchas-publicas` mostró la cotización del bloque
21:00–22:00 por S/ 70.00; no se guardó ni bloqueó horario. Se revisó la vista pública en
navegador; no se probó en dispositivos físicos ni con viewport móvil.

El seeder conserva seis cuentas, dos empresas, cuatro sedes y seis canchas; publica una
cancha demostrativa en cada empresa y conserva 22 tarifas de ejemplo. Los datos locales y
sus credenciales siguen separados del documento versionado. Al cierre de Fase 3D, la Fase 4
no había comenzado; la implementación posterior de 4A se registra a continuación.

## Fase 4A — Verificación final (24 de octubre de 2026)

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 115 aprobadas, 0 fallidas (260,81 s) |
| Frontend Vitest | 105 aprobadas, 0 fallidas (5,36 s) |
| Total automatizado | 220 aprobadas, 0 fallidas, 0 omitidas |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff | Sin errores |
| Vite build | Compilación correcta (1.893 módulos; 2,53 s) |
| Migración `reservas.0001_initial` | Aplicada a PostgreSQL local |

La suite final de backend se ejecutó desde `backend` con
`pytest tests -q --basetemp .pytest-f4a-complete-final-20261024`. Incluyó la prueba de
concurrencia de reservas en PostgreSQL, restricciones GiST, expiración, permisos y pruebas
del generador demo. Cuatro advertencias provienen de tests que sustituyen `DATABASES` al
comprobar las guardas del seeder; no hubo fallos.

La verificación frontend incluyó los flujos de solicitud, conflicto, sesión vencida,
cancelación y actualización de disponibilidad, además de los componentes compartidos. La
prueba focalizada de calendario y reservas obtuvo 15 aprobadas en 24,20 s en backend; los
tests frontend focalizados de Fase 3D/4A obtuvieron 15 aprobadas. Playwright no está instalado,
así que no se ejecutó una prueba E2E automatizada con ese navegador.

`showmigrations reservas` confirmó `[X] 0001_initial`. El seeder local, bajo sus guardas
explícitas de desarrollo, terminó con seis cuentas, dos empresas, cuatro sedes, seis canchas,
22 tarifas y tres reservas demo. Conservó las contraseñas locales existentes y no creó pagos.
El plazo inicial de 15 minutos es configurable y continúa pendiente de aprobación comercial.
No se implementaron WebSockets, pagos, QR ni confirmación de reserva.

## Fase 4B — Verificación final (25 de octubre de 2026)

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 123 aprobadas, 0 fallidas, 1 omitida (380,20 s) |
| Frontend Vitest | 111 aprobadas, 0 fallidas (6,58 s) |
| Playwright E2E / Chromium | 1 aprobada, 0 fallidas (38,10 s) |
| Total automatizado | 235 aprobadas, 0 fallidas, 1 omitida |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff | Sin errores |
| Vite build | Compilación correcta (1.896 módulos; 6,95 s) |

El backend completo se ejecutó con `pytest tests -q --basetemp .pytest-f4b-complete-final-20261024`.
Incluyó permisos multiempresa, transacciones de
reservas, eventos Channels, expiración, reconexión/validación de sesiones y separación por
cancha. Las cuatro advertencias fueron de tests existentes que sustituyen `DATABASES` para
comprobar las guardas del seeder; no hubo fallos. La última versión de los servicios WebSocket
también pasó la ejecución focalizada `pytest tests/test_fase4b_websocket.py -q --basetemp .pytest-f4b-websocket-final-20261025`: 7 aprobadas, 1 omitida (21,39 s).

`npm run test:run -- --reporter=dot` aprobó 111 tests en 15 archivos. Incluye apertura,
filtrado de eventos, cambio de cancha/fecha, reconexión limitada, actualización REST, cierre de
socket, invalidación comunicada de una selección y tema claro/oscuro. La configuración de
Vitest excluye `frontend/e2e/` para que los specs Playwright se ejecuten con su runner propio.

`npm run test:e2e -- --reporter=line` aprobó el escenario de dos jugadores en contextos
Chromium separados: la retención creada en A apareció en B sin recarga y la cancelación la
liberó. El setup usó el generador idempotente protegido por DEBUG/PostgreSQL loopback y puertos
locales 18200/15173. No se ejecutó contra producción.

La única prueba omitida necesita un servidor Redis real mediante `ALTOQUE_TEST_REDIS_URL`.
Este entorno no tiene Redis disponible, así que Channels se verificó con la capa InMemory y la
integración con Redis queda pendiente de ejecutar en un entorno que lo proporcione. La
configuración de producción sí exige Redis cuando `DEBUG=False`; esa exigencia de arranque se
valida en configuración, pero no equivale a una prueba de integración Redis.

## Fase 4C — Verificación final (25 de octubre de 2026)

| Capa | Resultado |
|---|---|
| Backend pytest / PostgreSQL | 129 aprobadas, 0 fallidas, 1 omitida (432,16 s) |
| Frontend Vitest | 117 aprobadas, 0 fallidas (16 archivos) |
| Playwright E2E / Chromium | 2 aprobadas, 0 fallidas (1,1 min) |
| Total automatizado | 248 aprobadas, 0 fallidas, 1 omitida |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff | Sin errores |
| Vite build | Compilación correcta (1.906 módulos) |
| Migraciones locales | `pagos.0001_initial` y `reservas.0002_remove_reserva_reserva_estado_valido_and_more` aplicadas |

El backend completo se ejecutó con `pytest tests -q --basetemp .pytest-f4c-final-20261025`;
la prueba focalizada de Fase 4C se volvió a ejecutar con `--reuse-db` y aprobó sus seis casos,
incluida la verificación de que WhatsApp muestre el importe del adelanto solicitado. La suite
completa conserva cuatro advertencias de pruebas del seeder que sustituyen `DATABASES`; no hubo
fallos. `npm run test:run -- --reporter=dot` aprobó los 117 tests de interfaz. Playwright ejecutó
la retención/liberación entre jugadores (4B) y el recorrido jugador-cajero de pago manual (4C).
Este último confirmó que declarar o aprobar un adelanto no confirma la reserva ni genera QR.

La inspección visual revisó el recorrido del jugador en móvil claro y el panel/modal de revisión
en escritorio oscuro, con el shell de administración y componentes compartidos. La referencia
Stitch «Matriz Horaria y Timeline de Canchas» se verificó para mantener su jerarquía operativa y
densidad de panel; los tokens oficiales de AlToque siguen definiendo color y tipografía. Las
capturas quedaron en `frontend/test-results/pagos-jugador-revision.png` y
`frontend/test-results/pagos-cajero-modal-oscuro.png`.

La prueba omitida del backend requiere Redis real mediante `ALTOQUE_TEST_REDIS_URL`. No hay
servidor, ejecutable, runtime de contenedores ni distribución WSL con Redis disponible en este
equipo; Channels quedó cubierto con InMemory y la integración Redis debe verificarse en un
entorno que lo proporcione. No se habilitó el procesamiento de pagos en producción; las
decisiones comerciales pendientes, el plazo provisional y el alcance excluido de Fase 4D siguen
documentados en `docs/DECISIONES.md`.
