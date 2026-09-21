"""
Django settings for the Shri Gouri Engineers portal.

Every deployment-specific value is read from the environment. A local .env file
is loaded for convenience in development; real environment variables always
take precedence. See .env.example for the full list.
"""

import os
from pathlib import Path

from .env import Env, ImproperlyConfigured, read_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env before reading any setting. Values already present in the real
# environment are left untouched.
read_dotenv(BASE_DIR / '.env', os.environ)
env = Env(os.environ)

# -- Core ---------------------------------------------------------------------
DEBUG = env.bool('DEBUG', False)

# In production a real key is mandatory. In development we fall back to an
# obviously-insecure value so a fresh checkout runs without ceremony.
SECRET_KEY = (
    env.str('SECRET_KEY', required=not DEBUG)
    or 'dev-only-insecure-key-do-not-use-in-production'
)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '[::1]'])

# A platform assigns the hostname only once the service exists, so it cannot be
# put in ALLOWED_HOSTS ahead of the first deploy. Each exposes it as an
# environment variable (host only, no scheme), so trust whichever is present.
# Harmless elsewhere: none of the variables is set.
#
# Vercel needs both of its own: VERCEL_URL is this deployment's unique URL and
# changes on every push, while VERCEL_PROJECT_PRODUCTION_URL is the stable
# alias visitors use. Missing the second means the production domain is
# rejected once DEBUG is off.
_platform_hosts = [
    host for host in (
        env.str('RENDER_EXTERNAL_HOSTNAME'),
        env.str('VERCEL_URL'),
        env.str('VERCEL_PROJECT_PRODUCTION_URL'),
    ) if host
]
CSRF_TRUSTED_ORIGINS_DEFAULT = []
for _platform_host in _platform_hosts:
    if _platform_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_platform_host)
    CSRF_TRUSTED_ORIGINS_DEFAULT.append('https://' + _platform_host)

if not DEBUG and ('*' in ALLOWED_HOSTS or not ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must list your real hostnames when DEBUG is off. '
        'A wildcard defeats the Host header check.'
    )

CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS', default=CSRF_TRUSTED_ORIGINS_DEFAULT
)

# -- URL mount point ----------------------------------------------------------
# Empty (the default) serves the app at the domain root. Set SCRIPT_PREFIX=/web
# to serve it under a sub-path behind a reverse proxy. Everything downstream --
# static URLs, media URLs, the PWA manifest, scope and service worker -- is
# derived from this single value.
_raw_prefix = (env.str('SCRIPT_PREFIX', '') or '').strip().strip('/')
URL_PREFIX = '/' + _raw_prefix if _raw_prefix else ''

if URL_PREFIX:
    FORCE_SCRIPT_NAME = URL_PREFIX
    USE_X_FORWARDED_HOST = env.bool('USE_X_FORWARDED_HOST', True)

# -- Applications -------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'pwa',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'crispy_forms',
    'crispy_tailwind',
    # Local apps
    'apps.accounts',
    'apps.machines',
    'apps.projects',
    'apps.notifications',
    'apps.website',
    'apps.portfolio',
    'apps.formbuilder',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.unread_notifications',
                'config.context_processors.company_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# -- Database -----------------------------------------------------------------
# DB_ENGINE selects the backend: mongodb (default), mysql, postgresql, or
# sqlite. The SQL backends are kept working because the application code is
# plain ORM, but the migrations are generated for MongoDB -- their ObjectId
# primary keys have no SQLite column type -- so switching engine means
# regenerating apps/*/migrations.
_DB_ENGINES = {
    'mysql': 'django.db.backends.mysql',
    'postgresql': 'django.db.backends.postgresql',
    'postgres': 'django.db.backends.postgresql',
    'sqlite': 'django.db.backends.sqlite3',
    'sqlite3': 'django.db.backends.sqlite3',
    'mongodb': 'django_mongodb_backend',
    'mongo': 'django_mongodb_backend',
}
_DB_DEFAULT_PORTS = {'mysql': '3306', 'postgresql': '5432', 'postgres': '5432'}

DB_ENGINE = env.str('DB_ENGINE', 'mongodb').lower()

# The test suite runs against whatever DB_ENGINE is configured; Django builds a
# separate test database and drops it afterwards, so the configured one is
# never touched. It used to fall back to SQLite so that `manage.py test` needed
# no database server, but the migrations now create ObjectId primary keys and
# SQLite has no column type for those, so the fallback failed before the first
# test ran. Point DB_ENGINE at a local mongod to run the suite offline.

if DB_ENGINE not in _DB_ENGINES:
    raise ImproperlyConfigured(
        'DB_ENGINE=' + repr(DB_ENGINE) + ' is not supported. Choose one of: '
        + ', '.join(sorted(_DB_ENGINES)) + '.'
    )

if DB_ENGINE in ('mongodb', 'mongo'):
    # MongoDB takes the whole connection string as HOST. parse_uri() used to
    # be the documented route but is deprecated in favour of this.
    #
    # Two things to know about running on MongoDB, both enforced by the
    # backend's own feature flags rather than by choice here:
    #   * There are no foreign keys. ForeignKey fields still work through the
    #     ORM, but referential integrity and ON DELETE are applied by Django,
    #     not by the database.
    #   * There are no CheckConstraints and no transactions, so
    #     transaction.atomic() is a no-op. Validation lives in the forms and
    #     in Model.clean(); see docs/MONGODB.md.
    DATABASES = {
        'default': {
            'ENGINE': _DB_ENGINES[DB_ENGINE],
            'HOST': env.str('MONGODB_URI', required=True),
            'NAME': env.str('DB_NAME', 'sge_portal'),
        }
    }
    # MongoDB's _id is an ObjectId, so the default primary key type has to
    # change; BigAutoField cannot be used.
    DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
    # Keeps embedded models out of migrations and dumpdata.
    DATABASE_ROUTERS = ['django_mongodb_backend.routers.MongoRouter']

    # Django's own apps hardcode AutoField primary keys in their AppConfigs and
    # in their shipped migrations, neither of which MongoDB can take. Swap in
    # the subclassed configs and point the three apps at migrations generated
    # for this backend. See config/mongo_apps.py.
    _MONGO_APP_CONFIGS = {
        'django.contrib.admin': 'config.mongo_apps.MongoAdminConfig',
        'django.contrib.auth': 'config.mongo_apps.MongoAuthConfig',
        'django.contrib.contenttypes': 'config.mongo_apps.MongoContentTypesConfig',
    }
    INSTALLED_APPS = [_MONGO_APP_CONFIGS.get(app, app) for app in INSTALLED_APPS]
    MIGRATION_MODULES = {
        'admin': 'config.mongo_migrations.admin',
        'auth': 'config.mongo_migrations.auth',
        'contenttypes': 'config.mongo_migrations.contenttypes',
    }

elif DB_ENGINE in ('sqlite', 'sqlite3'):
    DATABASES = {
        'default': {
            'ENGINE': _DB_ENGINES[DB_ENGINE],
            # SQLITE_NAME, not DB_NAME: DB_NAME holds the name of a MySQL or
            # PostgreSQL database, and reusing it here creates a stray file of
            # that name in the project root the first time anyone switches
            # engine for a quick run.
            'NAME': env.str('SQLITE_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _DB_ENGINES[DB_ENGINE],
            'NAME': env.str('DB_NAME', required=True),
            'USER': env.str('DB_USER', required=True),
            'PASSWORD': env.str('DB_PASSWORD', ''),
            'HOST': env.str('DB_HOST', '127.0.0.1'),
            'PORT': env.str('DB_PORT', _DB_DEFAULT_PORTS[DB_ENGINE]),
            # Reuse connections between requests instead of reconnecting on
            # every one; the health check stops a dropped socket being handed
            # to a view. Both matter against a managed or remote server.
            'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', 60),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {},
        }
    }

    _db_options = DATABASES['default']['OPTIONS']
    if DB_ENGINE == 'mysql':
        _db_options.update({
            'charset': 'utf8mb4',
            # STRICT_TRANS_TABLES makes MySQL reject bad values rather than
            # silently truncating them. Leave it on.
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': env.int('DB_CONNECT_TIMEOUT', 10),
        })
        # Managed MySQL providers (Aiven, RDS, TiDB) require TLS; a local
        # server does not. Two ways to enable it:
        #
        #   DB_SSL_CA=/path/to/ca.pem  encrypted AND the server certificate is
        #                              verified against that CA. Preferred.
        #   DB_SSL=true                encrypted, but the certificate is NOT
        #                              verified. Use only where placing the CA
        #                              file on the host is impractical; it
        #                              stops passive eavesdropping but not an
        #                              active man-in-the-middle.
        _db_ssl_ca = env.str('DB_SSL_CA')
        if _db_ssl_ca:
            _db_options['ssl'] = {'ca': _db_ssl_ca}
        elif env.bool('DB_SSL', False):
            _db_options['ssl'] = {'check_hostname': False, 'verify_mode': False}
    else:
        _db_options['connect_timeout'] = env.int('DB_CONNECT_TIMEOUT', 10)
        _db_sslmode = env.str('DB_SSLMODE')
        if _db_sslmode:
            _db_options['sslmode'] = _db_sslmode

if DB_ENGINE not in ('mongodb', 'mongo'):
    # On MongoDB this is ObjectIdAutoField, set in the database block above.
    DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -- Internationalisation -----------------------------------------------------
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = env.str('TIME_ZONE', 'Asia/Kolkata')
USE_I18N = True
USE_TZ = True

# -- Static and media files ---------------------------------------------------
STATIC_URL = URL_PREFIX + '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
# The manifest (hashed-filename) storage is correct for production but makes
# every missing reference a hard error, which is unhelpful while developing.
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedStaticFilesStorage' if DEBUG
    else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
)
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365

MEDIA_URL = URL_PREFIX + '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cap uploads so one request cannot exhaust memory or disk.
MAX_UPLOAD_SIZE_MB = env.int('MAX_UPLOAD_SIZE_MB', 10)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# -- Authentication redirects -------------------------------------------------
# URL pattern names, not reverse_lazy(). Django resolves a name through
# resolve_url() at the point of use, which honours SCRIPT_PREFIX exactly as
# reverse_lazy did. A lazy object here is actively harmful: anything that
# serialises or prints the settings -- Vercel's build step reads them and calls
# json.dumps on them -- forces the lazy value, which imports the URLconf and
# therefore the models before django.setup() has run, and the import fails with
# AppRegistryNotReady.
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# -- Sessions and security ----------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = env.int('SESSION_COOKIE_AGE', 60 * 60 * 24 * 14)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

if not DEBUG:
    # Behind a TLS-terminating proxy Django only learns the original scheme
    # from this header; without it SECURE_SSL_REDIRECT can redirect forever.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', True)
    CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', True)
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 365)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', False)

# -- Caching ------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sge-default',
        'TIMEOUT': 300,
    }
}

# -- Email --------------------------------------------------------------------
# Development defaults to the console backend, so no credentials are needed and
# nothing is accidentally sent to a real client address.
EMAIL_BACKEND = env.str(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = env.str('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', 10)
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@localhost')
SERVER_EMAIL = env.str('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# -- REST framework -----------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': env.int('API_PAGE_SIZE', 20),
    'EXCEPTION_HANDLER': 'apps.projects.api_views.api_exception_handler',
}

# Page size for the server-rendered list views.
PAGE_SIZE = env.int('PAGE_SIZE', 20)

# -- Company details (shown on the site and in invoice PDFs) ------------------
COMPANY_NAME = env.str('COMPANY_NAME', 'Shri Gouri Engineers')
COMPANY_PHONE = env.str('COMPANY_PHONE', '')
COMPANY_EMAIL = env.str('COMPANY_EMAIL', '')
COMPANY_ADDRESS = env.str('COMPANY_ADDRESS', '')
COMPANY_GSTIN = env.str('COMPANY_GSTIN', '')
SITE_URL = env.str('SITE_URL', 'http://127.0.0.1:8000')

# -- Progressive Web App ------------------------------------------------------
# Icons and the service worker are resolved from URL_PREFIX so the PWA works
# both at the domain root and under a sub-path. The project overrides
# templates/pwa.html, templates/manifest.json and templates/offline.html:
# django-pwa's bundled versions hardcode root-absolute paths, which 404 under
# any non-root prefix and stop the app being installable.
PWA_APP_NAME = env.str('PWA_APP_NAME', 'Shri Gouri Engineers')
PWA_APP_SHORT_NAME = env.str('PWA_APP_SHORT_NAME', 'SGE Portal')
PWA_APP_DESCRIPTION = env.str(
    'PWA_APP_DESCRIPTION',
    'Project tracking portal for Shri Gouri Engineers precision machining clients.',
)
PWA_APP_THEME_COLOR = '#ea580c'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL = URL_PREFIX + '/dashboard/'
PWA_APP_SCOPE = URL_PREFIX + '/'
PWA_APP_ROOT_URL = URL_PREFIX + '/'
PWA_APP_FETCH_URL = URL_PREFIX + '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'en-GB'
PWA_APP_DEBUG_MODE = DEBUG
PWA_SERVICE_WORKER_PATH = str(BASE_DIR / 'static' / 'js' / 'serviceworker.js')

PWA_APP_ICONS = [
    {'src': STATIC_URL + 'icons/icon-192x192.png', 'sizes': '192x192', 'type': 'image/png'},
    {'src': STATIC_URL + 'icons/icon-512x512.png', 'sizes': '512x512', 'type': 'image/png'},
]
# A maskable icon lets Android draw the icon in the launcher's own shape
# instead of boxing it. Chrome wants it declared as a separate entry.
PWA_APP_ICONS_MASKABLE = [
    {'src': STATIC_URL + 'icons/icon-maskable-192x192.png', 'sizes': '192x192',
     'type': 'image/png', 'purpose': 'maskable'},
    {'src': STATIC_URL + 'icons/icon-maskable-512x512.png', 'sizes': '512x512',
     'type': 'image/png', 'purpose': 'maskable'},
]
PWA_APP_ICONS_APPLE = [
    {'src': STATIC_URL + 'icons/icon-192x192.png', 'sizes': '192x192'},
]
PWA_APP_SPLASH_SCREEN = []
PWA_APP_SCREENSHOTS = []
PWA_APP_SHORTCUTS = [
    {'name': 'My Projects', 'short_name': 'Projects',
     'url': URL_PREFIX + '/dashboard/projects/',
     'icons': [{'src': STATIC_URL + 'icons/icon-192x192.png', 'sizes': '192x192'}]},
    {'name': 'Notifications', 'short_name': 'Alerts',
     'url': URL_PREFIX + '/notifications/',
     'icons': [{'src': STATIC_URL + 'icons/icon-192x192.png', 'sizes': '192x192'}]},
]

# -- Logging ------------------------------------------------------------------
LOG_LEVEL = env.str('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')
LOG_DIR = BASE_DIR / 'logs'
LOG_TO_FILE = env.bool('LOG_TO_FILE', not DEBUG)
if LOG_TO_FILE:
    LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django.db.backends': {
            # Query logging is extremely noisy; opt in explicitly.
            'handlers': ['console'],
            'level': env.str('DB_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

if LOG_TO_FILE:
    LOGGING['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': str(LOG_DIR / 'app.log'),
        'maxBytes': 5 * 1024 * 1024,
        'backupCount': 5,
        'formatter': 'verbose',
        'encoding': 'utf-8',
    }
    LOGGING['root']['handlers'].append('file')
    LOGGING['loggers']['apps']['handlers'].append('file')
