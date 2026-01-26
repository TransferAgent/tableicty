import os
import environ
from pathlib import Path

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ==============================================================================
# SSM Parameter Resolution Helper (AWS App Runner Fallback)
# ==============================================================================
# This function detects if an environment variable contains an SSM ARN and
# automatically fetches the actual secret value from AWS Systems Manager.
# This is a fallback for when App Runner's SSM resolution doesn't work.
# ==============================================================================

def resolve_ssm_parameter(env_var_name, default=''):
    """
    Fetch environment variable and resolve it if it's an SSM ARN.
    
    Args:
        env_var_name: Name of the environment variable
        default: Default value if not found
    
    Returns:
        Resolved value (from SSM if ARN, or direct value)
    """
    value = os.environ.get(env_var_name, default)
    
    if not value or not isinstance(value, str):
        return value
    
    # Check if this is an SSM ARN
    if value.startswith('arn:aws:ssm:'):
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Parse ARN: arn:aws:ssm:REGION:ACCOUNT:parameter/PATH
            arn_parts = value.split(':')
            if len(arn_parts) < 6:
                return value
            
            region = arn_parts[3]
            # Everything after 'parameter' is the path
            parameter_path = ':'.join(arn_parts[5:]).replace('parameter', '', 1)
            
            # Fetch from SSM Parameter Store
            ssm = boto3.client('ssm', region_name=region)
            response = ssm.get_parameter(
                Name=parameter_path,
                WithDecryption=True
            )
            
            return response['Parameter']['Value']
            
        except Exception as e:
            raise Exception(f"Failed to resolve SSM parameter {env_var_name}: {str(e)}")
    
    # Not an ARN, return as-is
    return value


# ==============================================================================
# Resolve Critical Environment Variables from SSM if needed
# ==============================================================================
IS_PRODUCTION = env.bool('IS_PRODUCTION', default=False)

if IS_PRODUCTION:
    # In production, resolve from SSM if ARNs are present
    _resolved_secret_key = resolve_ssm_parameter('SECRET_KEY')
    _resolved_database_url = resolve_ssm_parameter('DATABASE_URL')
    _resolved_pgcrypto_key = resolve_ssm_parameter('PGCRYPTO_KEY')
    _resolved_redis_url = resolve_ssm_parameter('REDIS_URL', default='')
    
    # Validate critical values were resolved
    if _resolved_database_url.startswith('arn:'):
        raise Exception("DATABASE_URL still contains ARN after resolution!")
    if _resolved_secret_key.startswith('arn:'):
        raise Exception("SECRET_KEY still contains ARN after resolution!")
    
    # Set resolved values in environment for django-environ to use
    os.environ['SECRET_KEY'] = _resolved_secret_key
    os.environ['DATABASE_URL'] = _resolved_database_url
    os.environ['PGCRYPTO_KEY'] = _resolved_pgcrypto_key
    if _resolved_redis_url:
        os.environ['REDIS_URL'] = _resolved_redis_url

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'localhost', 
    '127.0.0.1', 
    '.replit.dev', 
    '.repl.co',
    'tableicty.com',
    '.tableicty.com',
    '.awsapprunner.com',
])

APPEND_SLASH = True

REFRESH_TOKEN_COOKIE_SETTINGS = {
    'key': 'refresh_token',
    'path': '/',
    'domain': None,
    'httponly': True,
    'secure': IS_PRODUCTION,
    'samesite': 'None' if IS_PRODUCTION else 'Lax',
    'max_age': 60 * 60 * 24 * 7,
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'axes',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'apps.core',
    'apps.api',
    'apps.reports',
    'apps.shareholder',
    'apps.deal_desk',
]

MIDDLEWARE = [
    'apps.core.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'apps.core.middleware.TenantMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

if not DEBUG:
    DATABASES['default']['CONN_MAX_AGE'] = 600
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

USE_S3 = env('USE_S3', default=False)

if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False
    
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    if not DEBUG:
        MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'tableicty - Transfer Agent API',
    'DESCRIPTION': 'Transfer Agent Platform for OTC Markets',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_OBTAIN_SERIALIZER': 'apps.shareholder.jwt.TenantTokenObtainPairSerializer',
}

# CORS Configuration - resolve from SSM in production
# Set CORS_ALLOW_ALL_ORIGINS=true in env vars to bypass CORS for debugging
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)

if IS_PRODUCTION:
    if not CORS_ALLOW_ALL_ORIGINS:
        _cors_origins_raw = resolve_ssm_parameter('CORS_ALLOWED_ORIGINS', default='')
        if _cors_origins_raw:
            CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_raw.split(',') if origin.strip()]
        else:
            CORS_ALLOWED_ORIGINS = [
                'https://tableicty.com',
                'https://www.tableicty.com',
            ]
    
    _csrf_origins_raw = resolve_ssm_parameter('CSRF_TRUSTED_ORIGINS', default='')
    if _csrf_origins_raw:
        CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins_raw.split(',') if origin.strip()]
    else:
        CSRF_TRUSTED_ORIGINS = [
            'https://tableicty.com',
            'https://www.tableicty.com',
        ]
else:
    CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
        'http://localhost:3000',
        'http://localhost:5000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5000',
        'http://127.0.0.1:5173',
        'https://tableicty.com',
        'https://www.tableicty.com',
    ])
    CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
        'http://localhost:3000',
        'http://localhost:5000',
        'http://localhost:5173',
    ])

CORS_ALLOW_CREDENTIALS = True

REDIS_URL = env('REDIS_URL', default=None)

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'ssl_cert_reqs': None,
            }
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5

PGCRYPTO_KEY = env('PGCRYPTO_KEY', default='development-encryption-key-32char')

# ==============================================================================
# EMAIL CONFIGURATION (AWS SES)
# ==============================================================================
# Global email toggle - set to 'false' to disable all email sending (useful when VPC blocks SES)
EMAIL_ENABLED = env.bool('EMAIL_ENABLED', default=True)

if IS_PRODUCTION:
    # SES API Email Backend (VPC-compatible, bypasses SMTP connectivity issues)
    EMAIL_BACKEND = 'django_ses.SESBackend'
    AWS_SES_REGION_NAME = 'us-east-1'
    AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
    DEFAULT_FROM_EMAIL = resolve_ssm_parameter('EMAIL_FROM_ADDRESS', default='noreply@tableicty.com')
    EMAIL_FROM_NAME = resolve_ssm_parameter('EMAIL_FROM_NAME', default='Tableicty')
else:
    # Development: Use console backend (prints to terminal) or configure local SMTP
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
    EMAIL_HOST = env('EMAIL_HOST', default='localhost')
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_HOST_USER = env('EMAIL_USERNAME', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_PASSWORD', default='')
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_USE_SSL = False
    DEFAULT_FROM_EMAIL = env('EMAIL_FROM_ADDRESS', default='noreply@tableicty.com')
    EMAIL_FROM_NAME = env('EMAIL_FROM_NAME', default='Tableicty')

if IS_PRODUCTION:
    STRIPE_SECRET_KEY = resolve_ssm_parameter('STRIPE_SECRET_KEY', default='')
    STRIPE_PUBLISHABLE_KEY = resolve_ssm_parameter('STRIPE_PUBLISHABLE_KEY', default='')
    STRIPE_WEBHOOK_SECRET = resolve_ssm_parameter('STRIPE_WEBHOOK_SECRET', default='')
else:
    STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
    STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
    STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

if IS_PRODUCTION:
    FRONTEND_URL = env('FRONTEND_URL', default='https://tableicty.com')
else:
    FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:5000')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
