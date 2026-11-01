# Comprobación SMTP de Fase 4D

## Verificación local de la cola

`backend/tests/test_fase4d_correos_smtp.py` inicia un servidor SMTP temporal enlazado solo a
`127.0.0.1` y a un puerto libre. Acepta destinatarios `@example.test` y rechaza los demás; no
usa un relay externo. El caso crea un correo pendiente, ejecuta `enviar_correos` por el backend
SMTP de Django y comprueba entrega al buzón local, incremento de intentos y cierre del registro.

Comando enfocado:

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m pytest tests/test_fase4d_correos_smtp.py -q
```

En el cierre 4D se ejecutó dentro de la suite completa de pytest y pasó. Esto valida el
procesamiento de la cola y el protocolo contra el SMTP local de prueba; no demuestra entrega
externa, reputación del remitente ni recepción en bandeja de entrada.

## Entrega con un proveedor real

La prueba con proveedor requiere un SMTP autorizado y configurar `EMAIL_BACKEND`, `EMAIL_HOST`,
`EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` y `DEFAULT_FROM_EMAIL`.
Las credenciales deben venir del gestor de secretos del entorno, nunca de Git ni de logs. Antes
de ejecutar `python manage.py enviar_correos`, el propietario debe autorizar el proveedor, el
remitente y un destinatario de prueba controlado. Después se debe verificar el resultado en el
proveedor y en esa bandeja, sin enviar correos a clientes.

No se configuró ni contactó un proveedor real en este cierre. La validación externa queda
**PENDIENTE** de configuración y autorización explícita.
