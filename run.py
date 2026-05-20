from app import app

# Gunicorn expects a WSGI callable named "app" in this module.
# Start with: gunicorn run:app