FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y libpq-dev && pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app"]