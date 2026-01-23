FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets the PORT env variable (default 8080)
ENV PORT=8080

# Run gunicorn
# workers=1 is fine for basic I/O bound index
# threads=8 allows concurrency
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
