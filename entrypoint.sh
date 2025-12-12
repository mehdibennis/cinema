#!/bin/sh
set -euo pipefail

: "${APP_ENV:=prod}"
: "${DJANGO_SETTINGS_MODULE:=meteostation.settings.prod}"
: "${RUNSERVER_PORT:=8000}"

echo "[entrypoint] APP_ENV=$APP_ENV"
echo "[entrypoint] DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
# ---- Pass-through for special commands (mypy, tests, manage, etc.) ----
if [ "$#" -gt 0 ]; then
  case "$1" in
    runserver|gunicorn|start|prod|"")
    # Continue normal flow
      ;;
    mypy)
      shift
      exec mypy --config-file pyproject.toml "$@"
      ;;
    manage)
      shift
      exec python manage.py "$@"
      ;;
    pytest|test)
      if [ "${MIGRATE_ON_TEST:-1}" = "1" ]; then
        python manage.py migrate --noinput
      fi
      shift
      exec pytest "$@"
      ;;
    *)
      exec "$@"
      ;;
  esac
fi


# Wait for services (same as previous version) ...

python manage.py migrate --noinput

if [ "${CREATE_DEFAULT_USERS:-1}" = "1" ]; then
  python manage.py create_default_users || echo "[entrypoint] Warning user creation"
fi

if [ "$APP_ENV" = "dev" ]; then
  echo "[entrypoint] Starting Django runserver (dev mode)..."
  exec python manage.py runserver_plus 0.0.0.0:$RUNSERVER_PORT
else
  echo "[entrypoint] Starting Gunicorn (prod mode)..."
  python manage.py collectstatic --noinput
  WORKERS=${WORKERS:-$(python -c 'import multiprocessing as m; print(max(2, m.cpu_count()*2 + 1))')}
  exec gunicorn meteostation.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKERS" \
    --worker-tmp-dir /dev/shm \
    --max-requests 1500 \
    --max-requests-jitter 200 \
    --timeout 30 \
    --graceful-timeout 30 \
    --log-level "${LOG_LEVEL:-info}" \
    --access-logfile -
fi