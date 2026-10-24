# TwinGuard AI service

Small FastAPI scaffold for the AI-service contract. `/health` reports that the process is up. `/layers` reads registered layers and their recorded row counts from `twinguard.dataset_catalog` using a read-only, short-timeout database connection. The service reads database credentials from the project-root `.env` file and never returns connection details. Forecast, uncertainty, impact, route and scenario are placeholders and return HTTP 501 until implemented.

From `D:\TIWNGUARD`, run this single command to serve locally only:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services\ai-service --host 127.0.0.1 --port 8000
```

The interactive API description is at `http://127.0.0.1:8000/docs`; the generated OpenAPI document is at `http://127.0.0.1:8000/openapi.json`. The design contract is `docs\api\ai-service.yaml`.
