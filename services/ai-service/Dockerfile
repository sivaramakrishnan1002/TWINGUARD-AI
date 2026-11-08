FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/ai-service:/app
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir \
    fastapi==0.162.0 \
    uvicorn==0.54.0 \
    pydantic==2.14.1 \
    rasterio==1.5.2 \
    "psycopg[binary]==3.3.6"     numpy==2.5.3     scipy==1.18.1
COPY ai-service/app /app/services/ai-service/app
COPY trackb/connectors/tn_reservoir /app/services/trackb/connectors/tn_reservoir
# B47: Lane A flood engine, packaged read-only; runs are written only to the mounted /app/data/v3/runs store.
COPY flood_engine /app/services/flood_engine
RUN chmod -R a-w /app/services/flood_engine     && mkdir -p /app/data/v3/runs
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
