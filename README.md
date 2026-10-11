# Urlabari Interior Decor — Staff Portal

Stock, staff, attendance & HR for **Urlabari Interior Decor** (Urlabari, Morang).  
Independent of the public website: https://www.urlabariinterior.com.np/

## Modules
- Stock (inventory, QR receive, low stock)
- Staff & roles & permissions
- Attendance (Nepal time + optional geofence)
- Leave / overtime / payroll
- Company settings, maintenance mode, PWA

## Default logins
| User | Password |
|------|----------|
| `admin` | `admin123` |
| `argon` | `argon123` |

If login fails once: set env `RESET_ADMIN_PASSWORD=1`, redeploy, then remove it.

## Local
```bash
pip install -r requirements.txt
python run.py
```
SQLite file: `instance/urlabari_interior.db`

## Vercel + Layerbase (PostgreSQL)

1. Create Postgres on **Layerbase** (or Neon/Aiven) → copy connection string  
2. Vercel project → import this repo / upload  
3. Environment variables:

```
SECRET_KEY=<long-random>
DATABASE_URL=postgresql://USER:PASS@HOST:PORT/DB?sslmode=require
FLASK_ENV=production

# Optional email
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_DEFAULT_SENDER=info@urlabariinterior.com.np
HOTEL_EMAIL=info@urlabariinterior.com.np

# Optional
HMS_SITE_URL=https://your-app.vercel.app
CLOUDINARY_URL=...
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
```

4. Deploy → open `/login` → `admin` / `admin123`  
5. Settings → Company → upload **logo** (PWA splash) + geofence lat/lng  

### Notes
- `connect_timeout` is only used for PostgreSQL (SQLite local is fine).
- Serverless uses `NullPool` so Layerbase connection limits stay healthy.
- Hotel/restaurant modules are not registered.

## PWA
Install from browser → splash shows company logo from Settings.

## Fix Vercel 404 NOT_FOUND
1. **Root Directory** in Vercel project settings must be the folder that contains `wsgi.py` and `vercel.json` (not a parent empty folder).
2. `vercel.json` must route all paths to `wsgi.py` (static is served by Flask).
3. Redeploy after fixing. Open `/login` if `/` still redirects oddly.
4. Required env: `SECRET_KEY`, `DATABASE_URL` (Layerbase Postgres).

