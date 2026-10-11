import os

# Vercel / serverless
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("FLASK_ENV", "production")

from app import create_app

app = create_app()

# Vercel Python runtime looks for `app` (WSGI)
