"""PWA manifest + icons using admin-uploaded company logo."""
import json
import os
from flask import Blueprint, Response, current_app, send_file, request, redirect

pwa_bp = Blueprint("pwa", __name__)


def _logo_url():
    try:
        from app.models.settings import BusinessSettings
        s = BusinessSettings.get_settings()
        path = (s.logo_path or s.favicon_path or "").strip()
        if not path:
            return None
        if path.startswith("http"):
            return path
        base = request.url_root.rstrip("/")
        rel = path.replace("static/", "").lstrip("/")
        return f"{base}/static/{rel}"
    except Exception:
        return None


@pwa_bp.route("/manifest.webmanifest")
def manifest():
    logo = _logo_url()
    if logo:
        icons = [
            {"src": logo, "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": logo, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    else:
        icons = [
            {"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    name = "Urlabari Interior Decor — Staff"
    try:
        from app.models.settings import BusinessSettings
        s = BusinessSettings.get_settings()
        if s and s.hotel_name:
            name = f"{s.hotel_name} — Staff"
    except Exception:
        pass
    data = {
        "name": name,
        "short_name": "UID Staff",
        "description": "Stock, staff and HR for Urlabari Interior Decor",
        "start_url": "/dashboard",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#f8f5ed",
        "theme_color": "#1c1c1c",
        "lang": "en-NP",
        "icons": icons,
    }
    return Response(
        json.dumps(data),
        mimetype="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )


@pwa_bp.route("/pwa-logo")
def pwa_logo():
    logo = _logo_url()
    if logo and logo.startswith("http"):
        return redirect(logo)
    path = os.path.join(current_app.static_folder or "", "img", "icon-512.png")
    if path and os.path.isfile(path):
        return send_file(path)
    return Response(status=404)
