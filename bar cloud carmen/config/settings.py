"""
Configuración de Django — Bar Cloud (cliente: Carmen).

Las claves y valores sensibles se leen del archivo .env (nunca en el código).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'si', 'sí')


def env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


# --- Seguridad ---------------------------------------------------------------
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = env_bool('DEBUG', False)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')


# --- Aplicaciones ------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Módulos del sistema (cada uno es una app dentro de apps/)
LOCAL_APPS = [
    'apps.usuarios',
    'apps.venta_directa',
    'apps.mesas',
    'apps.productos',
    'apps.inventario',
    'apps.ventas',
    'apps.proveedores',
    'apps.reportes',
    'apps.configuracion',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.usuarios.context_processors.barcloud',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# --- Base de datos -----------------------------------------------------------
# Por ahora SQLite. Cuando se defina el hosting se cambia a PostgreSQL / MySQL.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv('SQLITE_NAME', 'db.sqlite3'),
    }
}


# --- Contraseñas -------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Idioma y zona horaria ---------------------------------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Santo_Domingo')
USE_I18N = True
USE_TZ = True


# --- Archivos estáticos y subidos --------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --- Login -------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'venta_directa:inicio'
LOGOUT_REDIRECT_URL = 'login'

# --- Negocio -----------------------------------------------------------------
# Solo son los valores iniciales: después el administrador los cambia en la pantalla Configuración
# (nombre, dirección, propina, ITBIS y textos del recibo).
NEGOCIO_NOMBRE = os.getenv('NEGOCIO_NOMBRE', 'Carmen')
NEGOCIO_DIRECCION = os.getenv('NEGOCIO_DIRECCION', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
