# AlToque Pichanga

Plataforma SaaS multiempresa para que complejos deportivos administren empresas, sedes,
personal y suscripciones. Las reservas y el directorio público completo pertenecen a
fases posteriores.

**Estado:** Fases 2, 3A y 3B implementadas. La siguiente entrega, Fase 3C (tarifas),
está pendiente de autorización.
Consulta [estado del proyecto](docs/ESTADO_PROYECTO.md), [documentación de arquitectura](docs/ARQUITECTURA.md),
[decisiones pendientes](docs/DECISIONES.md), [resultados de pruebas](docs/PLAN_PRUEBAS.md)
y la [guía de cuentas locales de prueba](docs/USUARIOS_PRUEBA.md).
Google OAuth real, SMTP y CI remoto requieren validación externa.

---

## Requisitos

- Python 3.12+
- Node.js 22+ y npm 11+
- PostgreSQL 17+
- Sistema operativo Windows, Linux o macOS

## 1. Backend

    cd backend
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env
    python manage.py migrate
    python manage.py runserver 127.0.0.1:8000

La API responde en http://127.0.0.1:8000/api/health/.

## 2. Frontend

    cd frontend
    npm install
    npm run dev

La aplicación queda disponible en http://localhost:5173/.

## 3. Pruebas y calidad

Desde backend:

    .\venv\Scripts\python.exe -m pytest tests
    .\venv\Scripts\ruff.exe check .
    .\venv\Scripts\python.exe manage.py check
    .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run

Desde frontend:

    npm run test:run
    npm run build

## 4. Estructura principal

    backend/apps/empresas
    backend/apps/sedes
    backend/apps/suscripciones
    backend/apps/usuarios
    backend/apps/canchas
    backend/apps/horarios
    backend/shared
    frontend/src/modules/empresas
    frontend/src/modules/administracion
    frontend/src/modules/autenticacion
    frontend/src/modules/horarios
    docs

Las migraciones nuevas deben aplicarse mediante migrate al preparar una base local o un
entorno nuevo. No se debe reiniciar una base que ya contenga usuarios o empresas.

