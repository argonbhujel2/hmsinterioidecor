import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-urlabari-interior-2026"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database: PostgreSQL if DATABASE_URL set, else SQLite (local)
    _db_url = os.environ.get("DATABASE_URL", "").strip()
    if _db_url:
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        _sqlite_path = BASE_DIR / "instance" / "urlabari_interior.db"
        try:
            _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            _t = _sqlite_path.parent / ".write_test"
            _t.write_text("ok")
            _t.unlink()
        except Exception:
            from pathlib import Path as _P
            _sqlite_path = _P("/tmp/urlabari_interior.db")
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_sqlite_path}"

    # Engine options: connect_timeout only for PostgreSQL (SQLite rejects it)
    _is_pg = SQLALCHEMY_DATABASE_URI.startswith("postgresql")
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        from sqlalchemy.pool import NullPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            "pool_pre_ping": True,
        }
        if _is_pg:
            SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"connect_timeout": 10}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": 2,
            "max_overflow": 0,
        }
        if _is_pg:
            SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"connect_timeout": 10}

    # Vercel filesystem is read-only except /tmp — use /tmp for local fallback uploads
    _upload_env = os.environ.get("UPLOAD_FOLDER", "").strip()
    if _upload_env:
        UPLOAD_FOLDER = _upload_env
    elif os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        UPLOAD_FOLDER = "/tmp/urlabari_interior_uploads"
    else:
        UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "ico"}

    # Session
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None  # avoid CSRF 400 on long forms
    WTF_CSRF_ENABLED = True

    # Hotel defaults (overridable in BusinessSettings)
    HOTEL_NAME = "Urlabari Interior Decor"
    BUSINESS_NAME = "Gypsum & Ceiling Solutions"
    HOTEL_ADDRESS = "Urlabari, Morang, Nepal"
    HOTEL_PHONE = "9816374804"
    DEFAULT_VAT_RATE = 13.0  # percent, inclusive
    CURRENCY = "Rs."
    TIMEZONE = "Asia/Kathmandu"  # Nepal time (NPT, UTC+5:45)
    CHECK_IN_TIME = "12:00"
    CHECK_OUT_TIME = "11:00"

    # Mail (optional)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    HOTEL_EMAIL = os.environ.get("HOTEL_EMAIL", "info@urlabariinterior.com.np")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "info@urlabariinterior.com.np")

    # Public website
    PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.urlabariinterior.com.np").rstrip("/")
    # HMS itself — QR order pages open here
    HMS_SITE_URL = os.environ.get("HMS_SITE_URL", "https://staff.urlabariinterior.com.np").rstrip("/")

    # Cloudinary (images/videos on Vercel)
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
