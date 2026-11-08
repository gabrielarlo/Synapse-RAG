FROM python:3.12-slim
WORKDIR /srv
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
COPY worker/worker.py .
CMD ["python", "worker.py"]
