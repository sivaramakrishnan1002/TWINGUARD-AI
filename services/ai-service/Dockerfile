FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/ai-service
WORKDIR /app
RUN python -m pip install --no-cache-dir \
    fastapi==0.162.0 \
    uvicorn==0.54.0 \
    pydantic==2.14.1 \
    "psycopg[binary]==3.3.6"
COPY app /app/services/ai-service/app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
