# ── Stage 1: Build dependencies ──────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production image ────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Don't run as root in production
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

# Production server: 4 Uvicorn workers behind Gunicorn process manager
CMD ["uvicorn", "application:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--timeout-keep-alive", "30"]
