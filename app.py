"""WSGI entrypoint for local ``python app.py``."""

import os

from bronze_injector.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", os.environ.get("PORT", 8000)))
    app.run(host="0.0.0.0", port=port, debug=True)
