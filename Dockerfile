# ============================================
# Stage 1: Builder - install Python dependencies
# ============================================
FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Stage 2: Runtime - minimal production image
# ============================================
FROM python:3.14-slim

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Force unbuffered Python output (critical for Railway log capture)
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd -r budget && useradd -r -g budget -d /app -s /bin/sh budget

WORKDIR /app

# Copy application code
COPY backend/ ./backend/
COPY frontend/templates/ ./frontend/templates/
COPY frontend/static/ ./frontend/static/

# Copy entrypoint and migration scripts
COPY docker/scripts/ ./docker/scripts/
RUN chmod +x ./docker/scripts/entrypoint.sh ./docker/scripts/scheduler.sh

# Create necessary directories
RUN mkdir -p ./backend/instance/uploads ./backend/logs \
    && chown -R budget:budget /app

USER budget

# Healthcheck (disabled for Railway which uses its own healthcheck mechanism)
# Uncomment for standalone Docker usage:
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD sh -c 'curl -f http://localhost:${PORT:-5000}/ || exit 1'

EXPOSE ${PORT:-5000}

ENTRYPOINT ["./docker/scripts/entrypoint.sh"]
