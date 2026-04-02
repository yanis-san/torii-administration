import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    import pymysql
    pymysql.install_as_MySQLdb()
    # Django 6 checks mysqlclient version metadata; PyMySQL exposes a legacy
    # compatibility string, so we override it to satisfy the backend check.
    pymysql.version_info = (2, 2, 1, 'final', 0)
    pymysql.__version__ = '2.2.1'
except ImportError:
    # PyMySQL may be unavailable in environments that do not use MySQL.
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# since settings is now in config/settings/base.py, BASE_DIR is parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Load environment variables from .env file (optional; cPanel can inject env vars directly)
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-$g*3j_mhpm*0uf^rt+)g8eh&2cxp2dh75+94^)c$_+#3lh%7dx')

# Admin URL prefix (can be overridden in production via env var).
DJANGO_ADMIN_UUID = os.getenv('DJANGO_ADMIN_UUID', 'admin').strip('/') or 'admin'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # Added for Whitenoise (dev support)
    'django.contrib.staticfiles',
    
    # Third party
    'tailwind',
    'theme', # We will configure tailwind in 'theme' app
    'django_htmx',

    # Local apps
    'core',
    'academics.apps.AcademicsConfig',
    'students.apps.StudentsConfig',  
    'finance',
    'documents',
    'cash',
    'reports',
    'emails',
    'inventory',
    'prospects.apps.ProspectsConfig',
    'tasks',
]

# Keep legacy integer PK behavior across apps (do not auto-switch to BigAutoField)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TAILWIND_APP_NAME = 'theme'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise right after security
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware', # HTMX
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = 'core.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles' # Required by whitenoise

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Optional fallback for hosts like cPanel where media can be served by Django app.
SERVE_MEDIA_WITH_DJANGO = env_bool('SERVE_MEDIA_WITH_DJANGO', False)

# Security / proxy configuration from env for seamless local/prod behavior.
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
