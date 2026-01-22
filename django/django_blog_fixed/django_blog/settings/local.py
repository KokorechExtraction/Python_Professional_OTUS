from .base import *  # noqa

# Local developer defaults
DEBUG = True

# Optionally load .env in local development (no effect if file missing).
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass
