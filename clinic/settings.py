"""
Django settings for the Piki Ora clinic backend (Assignment 2).

This is the API-only version of the project. Where Assignment 1 rendered
HTML templates, this build exposes everything through the Django REST
Framework and lets the React frontend do the rendering.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Pull in anything from a local .env file (SECRET_KEY, DATABASE_URL, etc.)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-dev')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Hosts are kept open for development / Vercel. Tighten in production.
ALLOWED_HOSTS = ['*']

# ── Apps ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework.authtoken',   # gives us token-based auth out of the box
    'corsheaders',                # lets the React dev server talk to us

    # Local
    'appointments',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # must sit high, before CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'clinic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'clinic.wsgi.application'

# ── Database ──────────────────────────────────────────────
# Use a hosted DB (e.g. Supabase/Postgres) in production via DATABASE_URL,
# otherwise fall back to a local SQLite file for development.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Our custom user model carries the patient/admin role.
AUTH_USER_MODEL = 'appointments.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Django REST Framework ─────────────────────────────────
REST_FRAMEWORK = {
    # Token auth for the SPA, session auth kept around so the browsable API
    # still works while developing.
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Lock everything down by default; individual views open up as needed.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ── CORS ──────────────────────────────────────────────────
# Allow the React dev server (Vite) and the deployed frontend to call the API.
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
# Extra origins (e.g. the Vercel URL) can be added through an env var.
_extra_origins = os.environ.get('CORS_EXTRA_ORIGINS', '')
if _extra_origins:
    CORS_ALLOWED_ORIGINS += [o.strip() for o in _extra_origins.split(',') if o.strip()]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
