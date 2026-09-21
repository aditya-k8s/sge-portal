FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# PyMySQL is pure Python, so no MySQL client headers or compiler toolchain are
# needed. The previous image installed build-essential and
# default-libmysqlclient-dev for mysqlclient, which this project does not use.
# Only Pillow needs system libraries.
RUN apt-get update && apt-get install --no-install-recommends -y \
      libjpeg62-turbo \
      zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Collect static assets at build time so the image can run read-only and the
# manifest of hashed filenames exists before the first request. A dummy key
# is fine here: collectstatic touches no secrets and no database.
RUN SECRET_KEY=build-only DEBUG=False ALLOWED_HOSTS=localhost DB_ENGINE=sqlite \
    python manage.py collectstatic --noinput

# Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/media /app/logs \
    && chown -R appuser:appuser /app/media /app/logs
USER appuser

EXPOSE 8000

# Gunicorn, not `manage.py runserver`. The development server is single
# threaded, serves static files inefficiently and is explicitly not intended
# for production use.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
