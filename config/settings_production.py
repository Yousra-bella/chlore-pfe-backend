from pathlib import Path
from datetime import timedelta
import os
import dj_database_url
 
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-chlore-pfe-cle-secrete-2025'
DEBUG = True
ALLOWED_HOSTS = ['*']
 
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Bibliothèques installées
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Notre application
    'chlore_api',
    'recipients', 
]
 
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # EN PREMIER !
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
 
ROOT_URLCONF = 'config.urls'
 
# ✅ Après
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],   # ← ajouté ici
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]
 
WSGI_APPLICATION = 'config.wsgi.application'
 
# ── BASE DE DONNÉES POSTGRESQL ─────────────────────────


DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://postgres:motdepasse@localhost:5432/chlore_db",
        conn_max_age=600,
    )
}
 
# Utiliser notre modèle User personnalisé
AUTH_USER_MODEL = 'chlore_api.User'
 
# ── DJANGO REST FRAMEWORK ──────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'chlore_api.authentication.QueryParamJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
 
# ── JWT CONFIGURATION ──────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}
 
# ── CORS : autorise l'app mobile ──────────────────────
CORS_ALLOW_ALL_ORIGINS = True  # Dev seulement !
 
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# ── Email Gmail SMTP ──────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = 'bellayoussra42@gmail.com'        # ← ton Gmail
EMAIL_HOST_PASSWORD = 'nbqm qoqa uari zolj'        # ← le code 16 caractères
DEFAULT_FROM_EMAIL  = f'ONEE Chlore <{EMAIL_HOST_USER}>'

# ── URL du backend pour les liens de reset ────────────────────
FRONTEND_URL = 'http://192.168.11.108:8000'
PASSWORD_RESET_REDIRECT_URL = 'password_reset_complete'
 
