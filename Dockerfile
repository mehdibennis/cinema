FROM python:3.12-slim as base

# Avoid interactive prompts during package installation inside the image
ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Silence pip warning about running as root inside containers
    PIP_ROOT_USER_ACTION=ignore
ENV TERM=dumb

WORKDIR /app

# Install minimal system dependencies needed for typical Python packages
RUN apt-get update \
     && apt-get install -yq --no-install-recommends \
         build-essential \
         gcc \
         libpq-dev \
         curl \
     && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt requirements.dev.txt ./

# Upgrade pip early
RUN python -m pip install --upgrade pip setuptools wheel --no-cache-dir

FROM base as dev
# Install development requirements
RUN if [ -f requirements.dev.txt ]; then python -m pip install -r requirements.dev.txt; fi
COPY . .
ENV PYTHONPATH=/app
# Default command for development target
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base as prod
# Install production requirements
RUN if [ -f requirements.prod.txt ]; then python -m pip install -r requirements.prod.txt; fi
COPY . .
ENV PYTHONPATH=/app
# Default command for production target; can be overridden by compose
CMD ["gunicorn", "cinema.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
