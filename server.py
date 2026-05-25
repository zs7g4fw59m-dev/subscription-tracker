"""Production WSGI entry point for gunicorn."""
from app import app, init_db

init_db()

if __name__ == "__main__":
    app.run()
