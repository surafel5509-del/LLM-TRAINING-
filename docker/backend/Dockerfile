FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
COPY backend/alembic.ini /app/alembic.ini
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/app
RUN mkdir -p /app/storage
CMD ["sh","-c","alembic -c /app/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
