import re
import sys
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
from corsheaders.defaults import default_headers
from django.db import models
from django.templatetags.static import static
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

SECRET_KEY = env('SECRET_KEY')

DEBUG = bool(env("DEBUG", default=0))
RUNNING_TESTS = "test" in sys.argv

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS").split(" ")

DOMAIN = env("DOMAIN")

SITE_URL = f"https://{DOMAIN}"

CORS_ALLOW_ALL_ORIGINS = True  # разрешает все домены
CORS_ALLOW_CREDENTIALS = True   #
# CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS").split(" ")
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type", "Accept"]
CORS_ALLOW_HEADERS = list(default_headers)
default_cors_origins = [] if DEBUG else [f"https://{DOMAIN}", f"https://www.{DOMAIN}"]
raw_cors_allowed_origins = env("CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOWED_ORIGINS = (
    [origin for origin in re.split(r"[\s,]+", raw_cors_allowed_origins.strip()) if origin]
    if raw_cors_allowed_origins.strip()
    else default_cors_origins
)
CORS_ALLOW_ALL_ORIGINS = env.bool(
    "CORS_ALLOW_ALL_ORIGINS",
    default=DEBUG and not CORS_ALLOWED_ORIGINS,
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


INSTALLED_APPS = [
    'modeltranslation',
    'unfold',
    "unfold.contrib.forms",
    "unfold.contrib.filters",  # optional, if special filters are needed  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",
    "unfold.contrib.simple_history",

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.postgres",

    'rest_framework',
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    "phonenumber_field",
    "import_export",
    'django_ckeditor_5',
    'django_countries',
    "simple_history",

    'account',
    'common',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'corsheaders.middleware.CorsMiddleware',
    'djangorestframework_camel_case.middleware.CamelCaseMiddleWare',

    'simple_history.middleware.HistoryRequestMiddleware',

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
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]


WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
    }
}


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


LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Asia/Bishkek'

USE_I18N = True

USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

STATICFILES_DIRS = [
    BASE_DIR / 'account/static/'
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# if not DEBUG:
#     sentry_sdk.init(
#         dsn=env('SENTRY_DSN'),
#         integrations=[DjangoIntegration()],
#         traces_sample_rate=0.5,  # Для мониторинга производительности. Можно уменьшить
#         send_default_pii=True,
#         environment="production",
#     )

PHONENUMBER_DEFAULT_REGION = 'KG'

LANGUAGES = (
    ('ru', 'Русский'),
    ('en', 'English'),
    ('ky', 'Кыргызча'),
)
MODELTRANSLATION_DEFAULT_LANGUAGE = 'ru'
MODELTRANSLATION_LANGUAGES = ('ru', 'en', 'ky')
MODELTRANSLATION_FALLBACK_LANGUAGES = {
    'default': ('ru',),
    'en': ('ru',),
    'ky': ('ru',),
}
MODELTRANSLATION_AUTO_POPULATE = True

LOGIN_REDIRECT_URL = reverse_lazy("admin:account_registrationsubmission_changelist")

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
LOG_FILE_PATH = env(
    "DJANGO_LOG_FILE",
    default="/tmp/django.log" if DEBUG or RUNNING_TESTS else str(BASE_DIR / "django.log"),
)

CSRF_TRUSTED_ORIGINS = [
    f"https://{DOMAIN}",
    f"https://www.{DOMAIN}",
]

AUTH_USER_MODEL = 'account.User'

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    'SHOW_COLLAPSED': True,
    'ENABLE_STACKTRACES': False,
    'DISABLE_PANELS': {
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'cachalot.panels.CachalotPanel',
    },
}

# Внутренние IP-адреса (для локальной разработки)
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

if DEBUG and not RUNNING_TESTS:
    INSTALLED_APPS += ['silk', "debug_toolbar",]
    MIDDLEWARE.insert(0, 'silk.middleware.SilkyMiddleware')
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware',)


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# False (по умолчанию): письма после регистрации отправляются сразу из веб-процесса (worker не обязателен).
# True: поставить в очередь Celery (нужен запущенный celery worker).
REGISTRATION_EMAIL_VIA_CELERY = env.bool("REGISTRATION_EMAIL_VIA_CELERY", default=False)


SPECTACULAR_SETTINGS = {
    'TITLE': 'ICEE',
    'DESCRIPTION': 'Your project description',
    'VERSION': '1.0.0',
    'SCHEMA_VERSION': '3.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CAMELIZE_NAMES': True,
    'COMPONENT_SPLIT_REQUEST': True,

    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields',
    ],

    'SERVE_PUBLIC': True,
    'SERVE_HTTPS': True,
    'SERVE_PERMISSIONS': ['config.permissions.IsSuperUser'],
    'SERVE_AUTHENTICATION': ['rest_framework.authentication.SessionAuthentication',]
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "AUTH_HEADER_TYPES": ("Bearer",),
    'UPDATE_LAST_LOGIN': True,
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "verbose",
        },

        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "filename": LOG_FILE_PATH,
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },

    "loggers": {
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },

        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },

        "django.request": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },

        "django.security": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },

        "gunicorn.error": {
            "level": "INFO",
        },

        "gunicorn.access": {
            "level": "WARNING",  # access лучше не INFO
        },

        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

customColorPalette = [
        {
            'color': 'hsl(4, 90%, 58%)',
            'label': 'Red'
        },
        {
            'color': 'hsl(340, 82%, 52%)',
            'label': 'Pink'
        },
        {
            'color': 'hsl(291, 64%, 42%)',
            'label': 'Purple'
        },
        {
            'color': 'hsl(262, 52%, 47%)',
            'label': 'Deep Purple'
        },
        {
            'color': 'hsl(231, 48%, 48%)',
            'label': 'Indigo'
        },
        {
            'color': 'hsl(207, 90%, 54%)',
            'label': 'Blue'
        },
    ]

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote',],
    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
                      'code','subscript', 'superscript', 'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|',  'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable',
                    ],
            'shouldNotGroupWhenFull': 'true'
        },
        'table': {
            'contentToolbar': [ 'tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties' ],
            'tableProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            },
            'tableCellProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}


def unfold_is_superuser(request):
    return bool(request.user and request.user.is_superuser)


def unfold_can_view_users(request):
    return unfold_is_superuser(request)


def unfold_can_view_visitors(request):
    return bool(request.user and request.user.is_staff and request.user.has_perm("account.view_exhibitionvisitor"))


def unfold_can_view_campaigns(request):
    return bool(request.user and request.user.is_staff and request.user.has_perm("account.view_registrationcampaign"))


def unfold_can_view_submissions(request):
    return bool(request.user and request.user.is_staff and request.user.has_perm("account.view_registrationsubmission"))


def unfold_can_use_checkin(request):
    return bool(request.user and request.user.is_staff)


def unfold_has_registration_workspace(request):
    return any(
        check(request)
        for check in (
            unfold_can_view_visitors,
            unfold_can_view_campaigns,
            unfold_can_view_submissions,
            unfold_can_use_checkin,
        )
    )


def unfold_has_system_workspace(request):
    return any(
        check(request)
        for check in (
            unfold_can_view_users,
            unfold_can_view_campaigns,
        )
    )

UNFOLD = {
    "SITE_TITLE": 'Регистрация и заявки',
    "SITE_HEADER": "Регистрация и заявки",
    # "SITE_SUBHEADER": "Регистрация и заявки",
    "SITE_URL": "/",
    "SITE_SYMBOL": "menu",  # symbol from icon set
    "SHOW_HISTORY": True, # show/hide "History" button, default: True
    "SHOW_VIEW_ON_SITE": True, # show/hide "View on site" button, default: True
    "SHOW_BACK_BUTTON": True,
    # "SITE_FAVICONS": [
    #     {
    #         "rel": "icon",
    #         "sizes": "32x32",
    #         "href": lambda request: static("iaeee_logo.png"),
    #     },
    # ],
    # "SITE_ICON": {
    #     "light": lambda request: static("iaeee_logo.png"),
    #     "dark": lambda request: static("iaeee_logo.png"),
    # },
    "SHOW_LANGUAGES": True,
    "BORDER_RADIUS": "6px",
    "COLORS": {
        "base": {
            "50": "249 250 251",
            "100": "243 244 246",
            "200": "229 231 235",
            "300": "209 213 219",
            "400": "156 163 175",
            "500": "107 114 128",
            "600": "75 85 99",
            "700": "55 65 81",
            "800": "31 41 55",
            "900": "17 24 39",
            "950": "3 7 18",
        },
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84"
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-600)",
            "default-dark": "var(--color-base-300)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-100)"
        }
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Рабочее место"),
                "collapsible": False,
                "permission": unfold_has_registration_workspace,
                "items": [
                    {
                        "title": _("Регистрации и формы"),
                        "icon": "event_note",
                        "link": reverse_lazy("admin:account_registrationcampaign_changelist"),
                        "permission": unfold_can_view_campaigns,
                    },
                    {
                        "title": _("Заявки"),
                        "icon": "assignment",
                        "link": reverse_lazy("admin:account_registrationsubmission_changelist"),
                        "permission": unfold_can_view_submissions,
                    },
                    {
                        "title": _("Сканирование билетов"),
                        "icon": "qr_code_scanner",
                        "link": reverse_lazy("exhibition_checkin"),
                        "permission": unfold_can_use_checkin,
                    },
                ],
            },
            {
                "title": _("Система"),
                "collapsible": False,
                "permission": unfold_has_system_workspace,
                "items": [
                    {
                        "title": _("Пользователи"),
                        "icon": "person",
                        "link": reverse_lazy("admin:account_user_changelist"),
                        "permission": unfold_can_view_users,
                    },
                    {
                        "title": _("Группы"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": unfold_can_view_users,
                    },
                    {
                        "title": _("API схема"),
                        "icon": "schema",
                        "link": reverse_lazy("schema"),
                        "permission": unfold_is_superuser,
                    },
                ],
            },
        ],
    }
}
