from .base import *  # noqa

DEBUG = False

# Faster password hashing for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Use in-memory email backend in tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
