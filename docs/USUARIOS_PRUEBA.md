# Usuarios de prueba — Fase 3B

Este fixture sirve para recorrer las vistas autenticadas de horarios con seis cuentas ficticias locales. Todas las cuentas usan el inicio de sesión normal de la aplicación (`/ingresar`, correo y contraseña); el comando no agrega rutas especiales ni omite permisos.

## Crear los datos

Desde PowerShell, ejecuta en el backend después de instalar dependencias y aplicar las migraciones:

```powershell
cd "D:\Descargas google\AlToquePichanga\backend"
python manage.py migrate
$env:ALTOQUE_PERMITIR_DATOS_DEMO = "1"
python manage.py generar_datos_demo
Remove-Item Env:ALTOQUE_PERMITIR_DATOS_DEMO
```

El comando solo funciona con `DEBUG=True`, PostgreSQL y `localhost`, `127.0.0.1` o `::1`. Si una condición falla, detiene la ejecución. No uses el opt-in en producción. Las contraseñas se guardan únicamente en `docs/USUARIOS_PRUEBA_LOCAL.md`, ignorado por Git; el comando no las imprime. Si el archivo ya existe con contenido ajeno al formato del seeder, no lo sobrescribe.

## Cuentas

| Correo | Rol | Alcance esperado |
|---|---|---|
| `demo-superadmin@example.test` | Superadministrador de plataforma | Lectura global y administración global según permisos reales. |
| `demo-dueno-a@example.test` | Dueño de empresa A | Ambas sedes de la empresa A; sin acceso a B. |
| `demo-dueno-b@example.test` | Dueño de empresa B | Ambas sedes de la empresa B; sin acceso a A. |
| `demo-admin-sede-a@example.test` | Administrador de sede | Solo la sede A Centro asignada. |
| `demo-cajero-a@example.test` | Cajero | Lectura en A Centro; no puede modificar horarios. |
| `demo-jugador@example.test` | Jugador | Sin membresías de empresa. |

Consulta las contraseñas locales en `docs/USUARIOS_PRUEBA_LOCAL.md` y entra por `/ingresar`.

## Escenario de horarios

El fixture crea dos empresas independientes, dos sedes por empresa y seis canchas. Cada sede tiene horario semanal. En A Centro hay una cancha que hereda el horario completo de la sede y otra con horario propio de lunes a viernes que hereda sábado y domingo. A Centro tiene una ampliación especial futura a nivel de sede y la cancha con horario propio tiene un cierre futuro por mantenimiento. Las excepciones incluyen el motivo marcado como demo.

Las entidades del fixture incluyen `[DEMO ALTOQUE]` y una marca estable. El comando es transaccional, repetible y aborta ante una colisión no marcada; no elimina cuentas ni datos ajenos. Las fechas de ampliación y mantenimiento se actualizan a la próxima fecha correspondiente al repetir la generación.

## Comprobaciones manuales

1. Inicia sesión por `/ingresar` con cada cuenta y verifica que su panel muestre su rol.
2. Como dueño A, confirma que no puedes consultar datos de B; repite como dueño B.
3. Como administrador y cajero, verifica que solo se muestre A Centro; intenta cambiar un horario como cajero y confirma que la API lo deniega.
4. Como superadministrador, consulta empresas, sedes y canchas de A y B.
5. Como jugador, confirma que no aparece ninguna membresía ni panel de empresa.
6. Abre la cancha heredada, la cancha con horario propio y sus excepciones para revisar la diferencia entre horario de sede, horario de cancha y cierres/ampliaciones.
