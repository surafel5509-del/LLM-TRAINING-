FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt psycopg[binary]==3.2.9
COPY backend /app/app
RUN mkdir -p /app/storage
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
