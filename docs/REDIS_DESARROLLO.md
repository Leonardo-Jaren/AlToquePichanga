# Redis aislado para desarrollo y prueba de Channels

`compose.redis.dev.yml` levanta Redis OSS 7.4 en un contenedor sin persistencia, con memoria
limitada y puerto publicado únicamente en `127.0.0.1:16379`. No comparte datos con otros
proyectos ni sustituye la prueba por una capa InMemory.

En PowerShell, desde la raíz del repositorio:

```powershell
.\backend\scripts\validar_redis.ps1
```

El script inicia el servicio y espera su comprobación de salud, verifica `PONG`, define
temporalmente `ALTOQUE_TEST_REDIS_URL=redis://127.0.0.1:16379/1` y ejecuta
`backend/tests/test_fase4b_websocket.py`. Restaura la variable de entorno al salir. El servicio
queda activo para inspección; se detiene con:

```powershell
docker compose -p altoque-pichanga-fase4d -f compose.redis.dev.yml down
```

La integración de Redis se omite si `ALTOQUE_TEST_REDIS_URL` no está configurada. En esta
máquina no está disponible Docker Desktop/Compose, por lo que la prueba local no pudo ejecutarse.
GitHub Actions sí levantó Redis OSS 7.4.12 y ejecutó la integración con URL explícita; el workflow
completo terminó con éxito y pytest registró 156 aprobadas, 0 omitidas. [Ejecución de CI](https://github.com/Leonardo-Jaren/AlToquePichanga/actions/runs/41344692313).
