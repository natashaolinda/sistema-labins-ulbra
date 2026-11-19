
"""
Configurações do Sistema Labins.

Responsável pela configuração dos aplicativos, banco de dados,
autenticação pelo Google, segurança, notificações por e-mail,
arquivos estáticos e armazenamento de relatórios.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ==============================================================================
# 1. DIRETÓRIO PRINCIPAL E VARIÁVEIS DE AMBIENTE
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# ==============================================================================
# 2. SEGURANÇA E AMBIENTE
# ==============================================================================

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'chave-padrao-insegura-fallback'
)

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.up.railway.app',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
]

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)


# ==============================================================================
# 3. APLICAÇÕES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'agendamentos',

    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]


# ==============================================================================
# 4. MIDDLEWARES
# ==============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]


ROOT_URLCONF = 'configuracao.urls'


# ==============================================================================
# 5. TEMPLATES HTML
# ==============================================================================

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


WSGI_APPLICATION = 'configuracao.wsgi.application'


# ==============================================================================
# 6. BANCO DE DADOS
# ==============================================================================

# O banco utilizado é definido pela variável DB_ENGINE.
# SQLite é o padrão quando a variável não está configurada.
# MySQL utiliza as credenciais definidas nas variáveis de ambiente.

DB_ENGINE = os.getenv(
    'DB_ENGINE',
    'sqlite'
).lower()


if DB_ENGINE == 'mysql':

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',

            'NAME': os.getenv('MYSQLDATABASE'),

            'USER': os.getenv('MYSQLUSER'),

            'PASSWORD': os.getenv('MYSQLPASSWORD'),

            'HOST': os.getenv('MYSQLHOST'),

            'PORT': os.getenv(
                'MYSQLPORT',
                '3306'
            ),

            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }

else:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',

            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ==============================================================================
# 7. VALIDADORES DE SENHA
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# ==============================================================================
# 8. IDIOMA E FUSO HORÁRIO
# ==============================================================================

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Araguaina'

USE_I18N = True

USE_TZ = True


# ==============================================================================
# 9. ARQUIVOS ESTÁTICOS
# ==============================================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# ==============================================================================
# 10. ARQUIVOS DE MÍDIA E RELATÓRIOS
# ==============================================================================

# Os relatórios gerados pelo sistema são armazenados em MEDIA_ROOT.
# No Railway, o caminho pode ser definido por um volume persistente.
# No ambiente local, os arquivos ficam na pasta media do projeto.
# O acesso aos relatórios deve ocorrer pelas rotas protegidas do sistema.

MEDIA_URL = '/media/'

MEDIA_ROOT = Path(
    os.getenv(
        'MEDIA_ROOT',
        str(BASE_DIR / 'media')
    )
)


# ==============================================================================
# 11. AUTENTICAÇÃO E SESSÃO
# ==============================================================================

SITE_ID = 1

LOGIN_REDIRECT_URL = '/sistema/reservar-laboratorio/'

ACCOUNT_LOGOUT_REDIRECT_URL = '/sistema/'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# O acesso ao sistema utiliza exclusivamente autenticação social.
SOCIALACCOUNT_ONLY = True

# O Google fornece o endereço de e-mail do usuário autenticado.
ACCOUNT_EMAIL_VERIFICATION = 'none'

LOGIN_URL = '/accounts/google/login/'


# ==============================================================================
# 12. CONFIGURAÇÕES DO DJANGO-ALLAUTH
# ==============================================================================

# Substitui a configuração descontinuada ACCOUNT_EMAIL_REQUIRED.
# O endereço de e-mail continua sendo um campo obrigatório.
# Os demais campos preservam a configuração padrão do Allauth.

ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]


# ==============================================================================
# 13. AUTENTICAÇÃO PELO GOOGLE
# ==============================================================================

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],

        'AUTH_PARAMS': {
            'access_type': 'online',
        },

        'FETCH_USERINFO': True,
    }
}

SOCIALACCOUNT_LOGIN_ON_GET = True

# Adaptador responsável por validar os e-mails autorizados.
SOCIALACCOUNT_ADAPTER = (
    'agendamentos.adapters.FiltroDominioAdapter'
)


# ==============================================================================
# 14. NOTIFICAÇÕES POR E-MAIL
# ==============================================================================

# O sistema utiliza o Google Apps Script para enviar notificações
# por HTTPS, sem depender de um servidor SMTP.

LABINS_EMAIL_API_URL = os.getenv(
    'LABINS_EMAIL_API_URL',
    ''
)

LABINS_API_KEY = os.getenv(
    'LABINS_API_KEY',
    ''
)

EMAIL_BACKEND = (
    'agendamentos.email_backend.AppsScriptEmailBackend'
)

DEFAULT_FROM_EMAIL = 'sistemalabins@gmail.com'

EMAIL_SUPORTE_TI = 'tiulbrapalmas@gmail.com'