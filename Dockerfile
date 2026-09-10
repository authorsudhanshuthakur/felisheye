FROM animcogn/face_recognition:cpu

ENV PYTHONUNBUFFERED=1 \
    PORT=10000 \
    HOST=0.0.0.0

WORKDIR /app

# Install lightweight web dependencies only (fastapi, uvicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app

# Ensure directories exist
RUN mkdir -p /app/data/photos /app/data/backups

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
