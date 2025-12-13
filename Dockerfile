# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies ONLY
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY . /app


# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim AS runtime
ENV TZ=UTC
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Install cron and timezone data
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron tzdata ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Configure timezone to UTC
RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime && echo "UTC" > /etc/timezone

# Copy Python environment from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY --from=builder /app /app

# Install cron job
RUN chmod 0644 /app/cron/2fa-cron && crontab /app/cron/2fa-cron

# Create persistent mount points
RUN mkdir -p /data /cron && chmod 0755 /data /cron
VOLUME ["/data", "/cron"]

# Ensure startup script is executable
RUN chmod +x /app/start.sh

EXPOSE 8080

# Start cron + API
CMD ["./start.sh"]
