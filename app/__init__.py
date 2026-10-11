
def _ensure_stock_categories():
    """Seed interior material categories."""
    from app.models.stock import StockCategory
    names = [
        "Gypsum Products",
        "Ceiling Products",
        "Accessories",
        "Tools & Hardware",
        "Paint & Finish",
        "Other",
    ]
    existing = {c.name.strip().lower() for c in StockCategory.query.all()}
    changed = False
    for i, name in enumerate(names, 1):
        if name.lower() not in existing:
            db.session.add(StockCategory(name=name, sort_order=i, is_active=True))
            changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()




def _ensure_roles_and_perms():
    """Idempotent roles + permissions for Urlabari Interior Decor (stock, staff, HR)."""
    from app.models.user import Role, Permission, RolePermission

    role_defs = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin / Manager"),
        ("kitchen", "Warehouse Staff"),
        ("reception", "Office Staff"),
        ("cashier", "Accounts"),
        ("staff", "Field Staff"),
        ("housekeeping", "Site Helper"),
    ]
    roles = {}
    for code, name in role_defs:
        r = Role.query.filter_by(code=code).first()
        if not r:
            r = Role(code=code, name=name)
            db.session.add(r)
            db.session.flush()
        elif r.name != name:
            r.name = name
        roles[code] = r

    # Full permission catalog required by routes
    all_codes = [
        # Core
        "dashboard.view",
        # Stock
        "stock.view", "stock.edit",
        # Staff / HR
        "staff.view", "staff.add", "staff.edit", "staff.disable", "staff.reset_pw",
        "staff.role", "staff.permissions", "staff.salary",
        "attendance.view", "attendance.approve",
        "leave.view", "leave.approve",
        "break.view", "break.approve",
        "overtime.view", "overtime.approve",
        "salary.view", "salary.create", "salary.edit", "salary.increment",
        "salary.deduction", "salary.consumption", "salary.fine", "salary.advance",
        "salary.payment", "salary.reports",
        "sessions.view", "sessions.force_logout",
        # Settings / audit / reports
        "settings.view", "settings.business", "settings.tax", "settings.payment",
        "settings.system",
        "audit.view", "audit.export",
        "reports.view", "reports.export",
    ]
    perms = {p.code: p for p in Permission.query.all()}
    for code in all_codes:
        if code not in perms:
            p = Permission(
                code=code,
                name=code.replace(".", " ").title(),
                module=code.split(".")[0],
            )
            db.session.add(p)
            db.session.flush()
            perms[code] = p

    def _grant(role_code, codes):
        r = roles.get(role_code)
        if not r:
            return
        for code in codes:
            p = perms.get(code)
            if not p:
                continue
            exists = RolePermission.query.filter_by(role_id=r.id, permission_id=p.id).first()
            if not exists:
                db.session.add(RolePermission(role_id=r.id, permission_id=p.id))

    # Super admin & admin — full catalog
    for role_code in ("super_admin", "admin"):
        _grant(role_code, all_codes)

    # Warehouse — stock full + own attendance
    _grant("kitchen", [
        "dashboard.view",
        "stock.view", "stock.edit",
        "attendance.view", "leave.view", "salary.view",
    ])

    # Office — staff view, attendance reports, limited settings
    _grant("reception", [
        "dashboard.view",
        "stock.view",
        "staff.view",
        "attendance.view", "leave.view", "leave.approve",
        "sessions.view",
    ])

    # Accounts — salary / payroll
    _grant("cashier", [
        "dashboard.view",
        "salary.view", "salary.create", "salary.edit", "salary.payment",
        "salary.reports", "salary.deduction", "salary.advance",
        "staff.view",
        "attendance.view",
    ])

    # Field staff — attendance self + stock view
    _grant("staff", [
        "dashboard.view",
        "stock.view",
        "attendance.view", "leave.view", "overtime.view", "salary.view",
    ])

    # Site helper — attendance only
    _grant("housekeeping", [
        "dashboard.view",
        "attendance.view", "leave.view",
    ])

    # Purge legacy hotel permissions from DB
    hotel_pref = ("rooms.", "bookings.", "menu.", "orders.", "kitchen.", "pos.", "billing.")
    for perm in list(Permission.query.all()):
        c = perm.code or ""
        if any(c.startswith(h) for h in hotel_pref) or c in ("settings.hotel", "settings.pos"):
            RolePermission.query.filter_by(permission_id=perm.id).delete(synchronize_session=False)
            try:
                from app.models.user import StaffPermission
                StaffPermission.query.filter_by(permission_id=perm.id).delete(synchronize_session=False)
            except Exception:
                pass
            db.session.delete(perm)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()




def _ensure_menu_categories_hms():
    """Legacy hotel menu categories — disabled for interior company."""
    return


import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from app.utils.timeutil import npt_now_naive

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        env = (os.environ.get("FLASK_ENV") or os.environ.get("VERCEL_ENV") or "development").lower()
        if env in ("production", "prod") or os.environ.get("VERCEL"):
            config_name = "production"
        else:
            config_name = "development"

    from app.config import config_by_name

    flask_app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    flask_app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure upload dirs (never crash on read-only FS like Vercel)
    try:
        os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)
        for sub in ("rooms", "menu", "qr", "logos", "signatures"):
            os.makedirs(os.path.join(flask_app.config["UPLOAD_FOLDER"], sub), exist_ok=True)
    except OSError:
        # Vercel / serverless: use /tmp
        flask_app.config["UPLOAD_FOLDER"] = "/tmp/urlabari_interior_uploads"
        try:
            os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)
            for sub in ("rooms", "menu", "qr", "logos", "signatures"):
                os.makedirs(os.path.join(flask_app.config["UPLOAD_FOLDER"], sub), exist_ok=True)
        except OSError:
            pass

    db.init_app(flask_app)
    login_manager.init_app(flask_app)
    migrate.init_app(flask_app, db)

    @flask_app.context_processor
    def _inject_push():
        try:
            from app.services.push_service import vapid_keys
            return {"vapid_public_key": vapid_keys()["public"]}
        except Exception:
            return {"vapid_public_key": ""}


    csrf.init_app(flask_app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.staff import staff_bp
    from app.routes.payroll import payroll_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp
    from app.routes.stock import stock_bp
    from app.routes.pwa import pwa_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(staff_bp, url_prefix="/staff")
    flask_app.register_blueprint(payroll_bp, url_prefix="/payroll")
    flask_app.register_blueprint(settings_bp, url_prefix="/settings")
    flask_app.register_blueprint(api_bp, url_prefix="/api")
    flask_app.register_blueprint(stock_bp, url_prefix="/stock")
    flask_app.register_blueprint(pwa_bp)

    # Exempt public QR order API from CSRF where needed (token-based)
    for _vf in ("qr_public.place_order", "qr_public.place_order_qr_path"):
        fn = flask_app.view_functions.get(_vf)
        if fn is not None:
            csrf.exempt(fn)
    # csrf.exempt pos.checkout
    # csrf.exempt pos.close_folio
    # csrf.exempt pos.folio_info

    @flask_app.before_request
    def maintenance_gate():
        from flask import request as req, render_template_string, session
        ep = (req.endpoint or "")
        if ep.startswith("static") or ep in ("auth.login", "auth.logout", "settings.maintenance"):
            return
        # Allow technical admin (argon) always
        from flask_login import current_user
        try:
            if current_user.is_authenticated and getattr(current_user, "username", "") == "argon":
                return
        except Exception:
            pass
        try:
            from app.models.settings import SystemSetting
            if SystemSetting.get("maintenance_mode") == "1":
                # other staff blocked except login
                if not current_user.is_authenticated:
                    return
                if getattr(current_user, "username", "") != "argon":
                    msg = SystemSetting.get("maintenance_message") or "Maintenance in progress."
                    logo = SystemSetting.get("logo_url") or ""
                    fav = SystemSetting.get("favicon_url") or ""
                    return render_template_string(
                        """<!DOCTYPE html><html><head><title>Maintenance</title>
                        {% if fav %}<link rel="icon" href="{{ fav }}">{% endif %}
                        <style>body{font-family:system-ui;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#0f172a;color:#fff;text-align:center;margin:0;padding:24px}
                        img{max-height:72px;margin-bottom:16px}</style></head><body>
                        {% if logo %}<img src="{{ logo }}" alt="Logo">{% endif %}
                        <div><h1>Under Maintenance</h1><p>{{ msg }}</p>
                        <p style="opacity:.7;margin-top:24px"><a href="{{ url_for('auth.logout') }}" style="color:#93c5fd">Logout</a></p></div>
                        </body></html>""",
                        msg=msg, logo=logo, fav=fav,
                    ), 503
        except Exception:
            pass

    @flask_app.before_request
    def validate_staff_session():
        """Force-logout works by deactivating StaffSession; reject if token inactive."""
        from flask import session, redirect, url_for, request as req, flash
        from flask_login import current_user, logout_user
        if not current_user.is_authenticated:
            return
        ep = req.endpoint or ""
        if ep.startswith("static") or ep in ("auth.login", "auth.logout"):
            return
        if not current_user.is_active:
            logout_user()
            flash("Your account is disabled.", "danger")
            return redirect(url_for("auth.login"))
        token = session.get("staff_session_token")
        from app.models.user import StaffSession
        import secrets
        from datetime import datetime
        if not token:
            # Recover: recreate session token instead of logging out (avoids CSRF loops)
            token = secrets.token_urlsafe(32)
            sess = StaffSession(
                user_id=current_user.id,
                session_token=token,
                ip_address=req.remote_addr,
                user_agent=(req.headers.get("User-Agent") or "")[:512],
                is_active=True,
                status="online",
            )
            db.session.add(sess)
            db.session.commit()
            session["staff_session_token"] = token
            return
        s = StaffSession.query.filter_by(
            session_token=token, user_id=current_user.id
        ).first()
        if s and not s.is_active:
            session.pop("staff_session_token", None)
            logout_user()
            flash("Your session was ended by an administrator. Please login again.", "warning")
            return redirect(url_for("auth.login"))
        if s:
            s.last_activity = npt_now_naive()
            s.status = "online"
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    @flask_app.errorhandler(403)

    def forbidden(e):
        return render_template("errors/403.html"), 403

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @flask_app.context_processor
    def inject_globals():
        from app.models.settings import BusinessSettings
        from flask_login import current_user

        settings = None
        try:
            settings = BusinessSettings.get_settings()
        except Exception:
            pass
        from app.utils.timeutil import format_npt, now_npt
        flask_app.jinja_env.filters['format_npt'] = format_npt
        return {
            "hotel_settings": settings,
            "current_user": current_user,
            "format_npt": format_npt,
            "now_npt": now_npt,
        }

    with flask_app.app_context():
        try:
            import app.models  # noqa: F401 — register all models
            try:
                import app.models.push  # noqa: F401
            except Exception:
                pass
            db.create_all()
        except Exception as e:
            flask_app.logger.warning("create_all skipped: %s", e)
        try:
            _ensure_hms_schema()
        except Exception:
            pass
        try:
            _ensure_schema_patches()
            try:
                _ensure_menu_categories_hms()
            except Exception:
                pass
            try:
                _ensure_roles_and_perms()
            except Exception:
                pass
        except Exception:
            pass
        try:
            _seed_if_empty()
        except Exception as e:
            flask_app.logger.warning("seed skipped: %s", e)
        try:
            _ensure_tech_admin()
        except Exception as e:
            flask_app.logger.warning("tech admin: %s", e)
        try:
            db.session.remove()
            db.engine.dispose()
        except Exception:
            pass

    @flask_app.teardown_appcontext
    def _shutdown_session(exception=None):
        try:
            db.session.remove()
        except Exception:
            pass

    return flask_app


def _ensure_schema_patches():
    """Add columns that models expect but older shared DBs may lack."""
    from sqlalchemy import text
    statements = [
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_email VARCHAR(200)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_ref VARCHAR(32)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(30)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_email VARCHAR(150)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS message TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS room_type_id INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS room_number VARCHAR(20)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS base_price_snapshot NUMERIC(10,2)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_nights INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS nightly_rates TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS source VARCHAR(30)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS advance_txn_number VARCHAR(100)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS advance_paid_claimed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_proof_url VARCHAR(500)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS client_ip VARCHAR(64)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS ip_location VARCHAR(255)",
        "ALTER TABLE staff_salary_profiles ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100)",
        "ALTER TABLE staff_salary_profiles ADD COLUMN IF NOT EXISTS bank_account_number VARCHAR(50)",
        "ALTER TABLE staff_salary_profiles ADD COLUMN IF NOT EXISTS wallet_provider VARCHAR(50)",
        "ALTER TABLE staff_salary_profiles ADD COLUMN IF NOT EXISTS wallet_account_number VARCHAR(50)",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS prep_time_minutes INTEGER",
        "ALTER TABLE business_settings ADD COLUMN IF NOT EXISTS attendance_lat DOUBLE PRECISION",
        "ALTER TABLE business_settings ADD COLUMN IF NOT EXISTS attendance_lng DOUBLE PRECISION",
        "ALTER TABLE business_settings ADD COLUMN IF NOT EXISTS attendance_radius_m INTEGER DEFAULT 200",
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS check_in_lat DOUBLE PRECISION",
        "ALTER TABLE stock_items ADD COLUMN IF NOT EXISTS qr_token VARCHAR(64)",
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS check_in_lng DOUBLE PRECISION",
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS check_out_lat DOUBLE PRECISION",
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS check_out_lng DOUBLE PRECISION",

    ]
    try:
        for sql in statements:
            try:
                db.session.execute(text(sql))
                db.session.commit()
            except Exception:
                db.session.rollback()
                # SQLite fallback without IF NOT EXISTS
                try:
                    if "customer_email" in sql:
                        db.session.execute(text("ALTER TABLE orders ADD COLUMN customer_email VARCHAR(200)"))
                        db.session.commit()
                except Exception:
                    db.session.rollback()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _seed_if_empty():
    """Seed roles, permissions, admin user, defaults when DB is empty."""
    from app.models.user import User, Role, Permission, RolePermission
    from app.models.settings import BusinessSettings, TaxSettings, POSSettings, WorkingHoursSettings
    from app.models.menu import MenuCategory
    from werkzeug.security import generate_password_hash

    # Keep role labels up to date on existing DBs
    waiter = Role.query.filter_by(code="staff").first()
    if waiter and waiter.name != "Field Staff":
        waiter.name = "Field Staff"
        db.session.commit()

    if Role.query.first():
        return

    # Roles
    roles_data = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin / Manager"),
        ("kitchen", "Warehouse / Field Staff"),
        ("reception", "Office Staff"),
        ("cashier", "Accounts"),
        ("staff", "Field Staff"),
        ("housekeeping", "Site Helper"),
    ]
    roles = {}
    for code, name in roles_data:
        r = Role(code=code, name=name)
        db.session.add(r)
        roles[code] = r
    db.session.flush()

    # Permissions (module.action)
    perm_codes = [
        "dashboard.view",
        "rooms.view", "rooms.add", "rooms.edit", "rooms.delete", "rooms.status", "rooms.qr",
        "bookings.view", "bookings.create", "bookings.edit", "bookings.cancel", "bookings.checkin", "bookings.checkout", "bookings.payment",
        "menu.view", "menu.add", "menu.edit", "menu.delete", "menu.price", "menu.availability", "menu.categories", "menu.image", "menu.website", "menu.qr_vis",
        "orders.view", "orders.details", "orders.accept", "orders.status", "orders.cancel", "orders.qr_manage",
        "kitchen.view", "kitchen.accept", "kitchen.preparing", "kitchen.ready", "kitchen.delivered", "kitchen.completed",
        "pos.open", "pos.create", "pos.discount", "pos.service", "pos.hold", "pos.complete",
        "billing.view", "billing.create", "billing.complete", "billing.print", "billing.reprint", "billing.void", "billing.refund",
        "staff.view", "staff.add", "staff.edit", "staff.disable", "staff.reset_pw", "staff.role", "staff.permissions", "staff.salary",
        "salary.view", "salary.create", "salary.edit", "salary.increment", "salary.deduction", "salary.consumption", "salary.fine", "salary.advance", "salary.payment", "salary.reports",
        "attendance.view", "attendance.approve", "leave.view", "leave.approve", "break.view", "break.approve", "overtime.view", "overtime.approve",
        "settings.view", "settings.business", "settings.tax", "settings.payment", "settings.system",
        "audit.view", "audit.export",
        "sessions.view", "sessions.force_logout",
        "reports.view", "reports.export",
    ]
    perms = {}
    for code in perm_codes:
        p = Permission(code=code, name=code.replace(".", " ").title())
        db.session.add(p)
        perms[code] = p
    db.session.flush()

    # Super admin & admin get all
    for role_code in ("super_admin", "admin"):
        for p in perms.values():
            db.session.add(RolePermission(role_id=roles[role_code].id, permission_id=p.id))

    # Kitchen
    for code in ["dashboard.view", "kitchen.view", "kitchen.accept", "kitchen.preparing", "kitchen.ready", "kitchen.delivered", "kitchen.completed", "orders.view", "orders.details"]:
        if code in perms:
            db.session.add(RolePermission(role_id=roles["kitchen"].id, permission_id=perms[code].id))

    # Reception
    for code in ["dashboard.view", "rooms.view", "rooms.status", "bookings.view", "bookings.create", "bookings.edit", "bookings.checkin", "bookings.checkout", "bookings.payment", "orders.view"]:
        if code in perms:
            db.session.add(RolePermission(role_id=roles["reception"].id, permission_id=perms[code].id))

    # Cashier
    for code in ["dashboard.view", "pos.open", "pos.create", "pos.discount", "pos.service", "pos.hold", "pos.complete", "billing.view", "billing.create", "billing.complete", "billing.print", "billing.reprint", "orders.view", "orders.status"]:
        if code in perms:
            db.session.add(RolePermission(role_id=roles["cashier"].id, permission_id=perms[code].id))

    # Waiter – self service + basic orders
    for code in ["dashboard.view", "attendance.view", "leave.view", "break.view", "overtime.view", "salary.view", "orders.view", "orders.accept", "menu.view", "rooms.view"]:
        if code in perms:
            db.session.add(RolePermission(role_id=roles["staff"].id, permission_id=perms[code].id))

    # Housekeeping – rooms dirty/clean
    if "housekeeping" in roles:
        for code in ["dashboard.view", "rooms.view", "rooms.status", "attendance.view", "leave.view"]:
            if code in perms:
                db.session.add(RolePermission(role_id=roles["housekeeping"].id, permission_id=perms[code].id))

    # Default admin user
    admin = User(
        username="admin",
        email="info@urlabariinterior.com.np",
        full_name="System Administrator",
        employee_id="UID-EMP-001",
        phone="9816374804",
        password_hash=generate_password_hash("admin123"),
        role_id=roles["super_admin"].id,
        is_active=True,
        department="Management",
    )
    db.session.add(admin)
    # Technical admin for maintenance
    if not User.query.filter_by(username="argon").first():
        tech = User(
            username="argon",
            email="admin@urlabariinterior.com.np",
            full_name="Technical Admin",
            is_active=True,
            password_hash=generate_password_hash("argon123"),
            role_id=roles["super_admin"].id,
        )
        db.session.add(tech)

    # Business settings
    bs = BusinessSettings(
        hotel_name="Urlabari Interior Decor",
        business_name="Gypsum & Ceiling Solutions",
        address="Urlabari-5, Morang",
        phone="9816374804",
        email="info@urlabariinterior.com.np",
        pan="",  # must be set before billing
        vat_number="",
        currency="Rs.",
        check_in_time="12:00",
        check_out_time="11:00",
        prepared_by_text="Urlabari Interior Decor\nGypsum & Ceiling Solutions",
    )
    db.session.add(bs)

    tax = TaxSettings(vat_rate=13.0, vat_inclusive=True, vat_enabled=True)
    db.session.add(tax)

    pos_s = POSSettings(service_charge_percent=0, default_payment_method="cash")
    db.session.add(pos_s)

    wh = WorkingHoursSettings(
        work_start="10:00",
        work_end="18:00",
        required_daily_hours=8.0,
        break_duration_minutes=60,
        grace_period_minutes=10,
        working_days_per_month=26,
        late_fine_enabled=False,
        early_fine_enabled=False,
        overtime_enabled=True,
        overtime_salary_enabled=True,
        overtime_rate_type="salary_based",
        overtime_multiplier=1.5,
    )
    db.session.add(wh)

    # Skip legacy hotel menu categories for interior company
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _ensure_hms_schema():
    from sqlalchemy import text
    patches = [
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS floor VARCHAR(20)",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS show_on_website BOOLEAN DEFAULT FALSE",
        # Do NOT bulk-update all rooms — public-admin rooms must stay True

        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255)",
    ]
    for sql in patches:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass


def _ensure_tech_admin():
    """Always ensure login works: admin/admin123 and argon/argon123 (create if missing)."""
    from app.models.user import User, Role
    from werkzeug.security import generate_password_hash
    import os

    role = Role.query.filter_by(code="super_admin").first()
    if not role:
        role = Role(code="super_admin", name="Super Admin")
        db.session.add(role)
        db.session.flush()
        # minimal admin role too
        if not Role.query.filter_by(code="admin").first():
            db.session.add(Role(code="admin", name="Admin / Manager"))

    def upsert(username, password, email, full_name):
        u = User.query.filter_by(username=username).first()
        force = os.environ.get("RESET_ADMIN_PASSWORD", "").strip() in ("1", "true", "yes")
        if u:
            if force:
                u.password_hash = generate_password_hash(password)
                u.is_active = True
                u.role_id = role.id
            elif not u.is_active:
                u.is_active = True
            return u
        u = User(
            username=username,
            email=email,
            full_name=full_name,
            is_active=True,
            password_hash=generate_password_hash(password),
            role_id=role.id,
        )
        db.session.add(u)
        return u

    upsert("admin", "admin123", "info@urlabariinterior.com.np", "System Administrator")
    upsert("argon", "argon123", "admin@urlabariinterior.com.np", "Technical Admin")
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
