FROM python:3.12-slim
WORKDIR /srv
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
COPY infra/seed.py ./seed.py
ENV SESSION_DB_PATH=/data/sessions.db
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
