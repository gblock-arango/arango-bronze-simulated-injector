"""Gunicorn entrypoint (``PYTHONPATH=src``)."""

from bronze_injector.app import create_app

app = create_app()
