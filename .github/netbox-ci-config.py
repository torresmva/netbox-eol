"""Minimal NetBox configuration for CI test runs (manage.py test netbox_eol).

Copied over netbox/netbox/netbox/configuration.py in the CI workflow. Points at
the Postgres/Redis service containers and enables the plugin. Not for production.
"""

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "netbox",
        "USER": "netbox",
        "PASSWORD": "netbox",
        "HOST": "localhost",
        "PORT": "5432",
        "CONN_MAX_AGE": 300,
    }
}

REDIS = {
    "tasks": {
        "HOST": "localhost",
        "PORT": 6379,
        "DATABASE": 0,
        "PASSWORD": "",
        "SSL": False,
    },
    "caching": {
        "HOST": "localhost",
        "PORT": 6379,
        "DATABASE": 1,
        "PASSWORD": "",
        "SSL": False,
    },
}

# CI-only; must be >= 50 characters. Never use a fixed key in production.
SECRET_KEY = "ci0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP"

PLUGINS = ["netbox_eol"]
