"""
WSGI config for django_blog project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Default to local settings; override via DJANGO_SETTINGS_MODULE in production.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings.local')

application = get_wsgi_application()
