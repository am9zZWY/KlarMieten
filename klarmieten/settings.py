"""
Django settings for klarmieten project
"""

import functools
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect environment
IS_VERCEL = os.environ.get('VERCEL', False)
IS_PROD = os.environ.get('ENVIRONMENT') == 'production' or IS_VERCEL
DEBUG = os.getenv("DEBUG", "False") == "True" and not IS_PROD

# SECURITY SETTINGS
# ------------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default-key")


# Lazy load environment variables only when needed
@functools.lru_cache(maxsize=None)
def get_file_encryption_key():
    """Lazy loading of encryption key to avoid file I/O during startup"""
    if "FILE_ENCRYPTION_KEY" in os.environ:
        print("Using encryption key from environment variable")
        return bytes.fromhex(os.environ["FILE_ENCRYPTION_KEY"])

    key_path = BASE_DIR / ".encryption_key"
    if key_path.exists():
        with open(key_path, "rb") as f:
            print("Using encryption key from file")
            return f.read()

    # Only import secrets if actually needed
    import secrets
    key = secrets.token_bytes(32)
    if not IS_VERCEL:
        with open(key_path, "wb") as f:
            f.write(key)
    print("Generated new encryption key")
    return key


# Define a property that loads the encryption key only when accessed
class LazySettings:
    @property
    def FILE_ENCRYPTION_KEY(self):
        return get_file_encryption_key()


lazy_settings = LazySettings()
FILE_ENCRYPTION_KEY = lazy_settings.FILE_ENCRYPTION_KEY

# Allowed hosts setup
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
if IS_VERCEL:
    ALLOWED_HOSTS.extend(['.vercel.app', '.now.sh'])

print(f"Running in {'production' if IS_PROD else 'development'} mode")
print(f"Allowed hosts: {ALLOWED_HOSTS}")

# APPLICATION SETTINGS
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Third party apps
    'widget_tweaks',

    # Local apps
    "customers",
    "payments",
    "contract_analysis",
    "klarmieten",

    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "klarmieten.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "klarmieten.wsgi.application"

# DATABASE SETTINGS
# ------------------------------------------------------------------------------
if IS_VERCEL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DATABASE"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOST"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "OPTIONS": {
                "sslmode": "require"
            }
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# MEDIA FILES
# ------------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "private_media"

# FILE UPLOAD SETTINGS
# ------------------------------------------------------------------------------
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# AUTHENTICATION SETTINGS
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "customers.User"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# STATIC FILES
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise optimized configuration
WHITENOISE_COMPRESS = True
WHITENOISE_KEEP_ONLY_HASHED_FILES = True

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Storage configuration
# ------------------------------------------------------------------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": STATICFILES_STORAGE,
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# CACHING
# ------------------------------------------------------------------------------
if IS_VERCEL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vercel-cache",
            "TIMEOUT": 300,  # 5 minutes
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-contracts",
        }
    }

# Simplified logging for faster startup
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING" if IS_PROD else "INFO",
    },
}

# STRIPE SETTINGS
# ------------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
DOMAIN = os.getenv('DOMAIN', 'http://localhost:3000')

# DEFAULT PRIMARY KEY FIELD TYPE
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# NAME OF THE APPLICATION
# ------------------------------------------------------------------------------
APP_NAME = "KlarMieten"

print("Settings loaded successfully")
