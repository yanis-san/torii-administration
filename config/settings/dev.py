from .base import *
import os
import sys

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Optional for live reload in dev
INSTALLED_APPS += ["django_browser_reload"]
MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]

SERVE_MEDIA_WITH_DJANGO = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('LOCAL_DB_NAME', os.getenv('DB_NAME', 'institut_torii_db')),
        'USER': os.getenv('LOCAL_DB_USER', os.getenv('DB_USER', 'root')),
        'PASSWORD': os.getenv('LOCAL_DB_PASSWORD', os.getenv('DB_PASSWORD', '')),
        'HOST': os.getenv('LOCAL_DB_HOST', os.getenv('DB_HOST', '127.0.0.1')),
        'PORT': os.getenv('LOCAL_DB_PORT', os.getenv('DB_PORT', '3306')),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Use SQLite for tests to avoid external DB permissions issues
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'TEST': {
                'NAME': ':memory:',
            },
        }
    }

# Development Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@institut-torii.dz'

# On windows some people need to manually specify npm path for tailwind dev
# Let's try standard first, user can uncomment and adjust if error
# NPM_BIN_PATH = "npm.cmd"
