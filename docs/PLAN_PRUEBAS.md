# Plan y resultados de pruebas — Fases 0, 1, 2, 3A y 3B

Actualizado: 18 de octubre de 2026 (America/Lima).

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

