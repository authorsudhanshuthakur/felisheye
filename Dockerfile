FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=10000 \
    HOST=0.0.0.0

# Minimal runtime dependencies only (no compilers, no cmake)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /app

# Install prebuilt binary wheels (takes ~20 seconds instead of gigabytes of compilation)
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=user:user . /app

RUN mkdir -p /app/data/photos /app/data/backups && \
    chown -R user:user /app/data

USER user

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
