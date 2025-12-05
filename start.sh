#!/bin/bash
set -e

echo "========================================"
echo "Starting tableicty Django Application"
echo "========================================"
echo ""

echo "--- Environment Check ---"
echo "IS_PRODUCTION: ${IS_PRODUCTION:-not set}"
echo "ALLOWED_HOSTS: ${ALLOWED_HOSTS:-not set}"
echo ""

echo "--- Checking DATABASE_URL ---"
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    exit 1
elif [[ "$DATABASE_URL" == arn:aws:ssm:* ]]; then
    echo "DATABASE_URL contains SSM ARN (will be resolved by Django)"
    echo "ARN: ${DATABASE_URL:0:60}..."
else
    echo "DATABASE_URL is set (length: ${#DATABASE_URL})"
fi
echo ""

echo "--- Checking SECRET_KEY ---"
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set!"
    exit 1
elif [[ "$SECRET_KEY" == arn:aws:ssm:* ]]; then
    echo "SECRET_KEY contains SSM ARN (will be resolved by Django)"
else
    echo "SECRET_KEY is set (length: ${#SECRET_KEY})"
fi
echo ""

echo "--- Checking PGCRYPTO_KEY ---"
if [ -z "$PGCRYPTO_KEY" ]; then
    echo "WARNING: PGCRYPTO_KEY is not set"
elif [[ "$PGCRYPTO_KEY" == arn:aws:ssm:* ]]; then
    echo "PGCRYPTO_KEY contains SSM ARN (will be resolved by Django)"
else
    echo "PGCRYPTO_KEY is set (length: ${#PGCRYPTO_KEY})"
fi
echo ""

echo "--- Checking REDIS_URL ---"
if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL is not set (optional)"
elif [[ "$REDIS_URL" == arn:aws:ssm:* ]]; then
    echo "REDIS_URL contains SSM ARN (will be resolved by Django)"
else
    echo "REDIS_URL is set (length: ${#REDIS_URL})"
fi
echo ""

echo "--- Python & Package Check ---"
python3 --version
echo ""

echo "--- Checking Python Dependencies ---"
if python3 -c "import django" 2>/dev/null; then
    echo "✅ Packages already installed (from build stage)"
else
    echo "⚠️  Packages not found, attempting to install..."
    python3 -m pip install --no-cache-dir -r requirements.txt || {
        echo "❌ Failed to install packages (network issue)"
        echo "Checking if packages are available locally..."
        python3 -c "import django" || exit 1
    }
fi
echo ""

echo "--- Testing Django Configuration ---"
python3 manage.py check
echo ""

echo "--- Running Database Migrations ---"
python3 manage.py migrate --noinput
echo ""

echo "--- Collecting Static Files ---"
python3 manage.py collectstatic --noinput
echo ""

echo "========================================"
echo "Starting Gunicorn Server..."
echo "========================================"
exec python3 -m gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    config.wsgi:application
