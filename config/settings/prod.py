from .base import *
import os
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if not os.getenv('DJANGO_ADMIN_UUID', '').strip():
    raise ImproperlyConfigured('DJANGO_ADMIN_UUID must be set in production environment variables.')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'institut_torii_db'),
        'USER': os.getenv('DB_USER', 'yanis'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'use_unicode': True,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

# WhiteNoise storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Static & Media paths (override to point to cPanel subdomain folders)
STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR / 'staticfiles')
MEDIA_ROOT = os.getenv('MEDIA_ROOT', BASE_DIR / 'media')

# Optional: allow Django app to serve media if cPanel static mapping is unavailable.
SERVE_MEDIA_WITH_DJANGO = os.getenv('SERVE_MEDIA_WITH_DJANGO', 'False').strip().lower() in {'1', 'true', 'yes', 'on'}

# Typical reverse proxy header on shared hosting / cPanel setups.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Production Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Ensure cookies are secure
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
