FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (git and docker cli to interact with docker socket if mounted)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["python3", "-m", "service.app"]
