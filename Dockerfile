FROM python:3.11-slim

# Non-sensitive environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IS_PRODUCTION=True
ENV ALLOWED_HOSTS=tableicty.com,api.tableicty.com
ENV CORS_ALLOWED_ORIGINS=https://tableicty.com
ENV SESSION_COOKIE_SECURE=True
ENV CSRF_COOKIE_SECURE=True

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120"]

