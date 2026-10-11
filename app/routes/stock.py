"""Stock management — Urlabari Interior Decor."""
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.stock import StockCategory, StockItem, StockMovement
from app.utils.decorators import permission_required
from app.utils.audit import log_activity
from app.utils.timeutil import npt_now_naive

stock_bp = Blueprint("stock", __name__)


def _dec(val, default="0"):
    try:
        return Decimal(str(val if val not in (None, "") else default))
    except Exception:
        return Decimal(default)


@stock_bp.route("/")
@login_required
@permission_required("stock.view")
def list_items():
    q = (request.args.get("q") or "").strip()
    cat_id = request.args.get("category_id", type=int)
    low = request.args.get("low")
    query = StockItem.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(StockItem.name.ilike(like), StockItem.sku.ilike(like)))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    items = query.order_by(StockItem.name).all()
    if low:
        items = [i for i in items if i.is_low]
    categories = StockCategory.query.filter_by(is_active=True).order_by(StockCategory.sort_order, StockCategory.name).all()
    low_count = sum(1 for i in StockItem.query.filter_by(is_active=True).all() if i.is_low)
    return render_template(
        "stock/list.html",
        items=items,
        categories=categories,
        q=q,
        cat_id=cat_id,
        low=bool(low),
        low_count=low_count,
    )


@stock_bp.route("/categories", methods=["GET", "POST"])
@login_required
@permission_required("stock.edit")
def categories():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if name:
            if not StockCategory.query.filter(db.func.lower(StockCategory.name) == name.lower()).first():
                db.session.add(StockCategory(name=name, sort_order=StockCategory.query.count() + 1))
                db.session.commit()
                flash(f"Category “{name}” added.", "success")
            else:
                flash("Category already exists.", "warning")
        return redirect(url_for("stock.categories"))
    cats = StockCategory.query.order_by(StockCategory.sort_order, StockCategory.name).all()
    return render_template("stock/categories.html", categories=cats)


@stock_bp.route("/categories/<int:cid>/delete", methods=["POST"])
@login_required
@permission_required("stock.edit")
def delete_category(cid):
    c = db.session.get(StockCategory, cid)
    if c:
        if StockItem.query.filter_by(category_id=c.id).count():
            flash("Category has items — reassign or deactivate items first.", "danger")
        else:
            db.session.delete(c)
            db.session.commit()
            flash("Category deleted.", "success")
    return redirect(url_for("stock.categories"))


@stock_bp.route("/add", methods=["GET", "POST"])
@login_required
@permission_required("stock.edit")
def add_item():
    categories = StockCategory.query.filter_by(is_active=True).order_by(StockCategory.name).all()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Name required.", "danger")
            return render_template("stock/form.html", item=None, categories=categories)
        item = StockItem(
            sku=(request.form.get("sku") or "").strip() or None,
            name=name,
            category_id=request.form.get("category_id", type=int) or None,
            unit=(request.form.get("unit") or "pcs").strip(),
            quantity=_dec(request.form.get("quantity")),
            reorder_level=_dec(request.form.get("reorder_level")),
            cost_price=_dec(request.form.get("cost_price")),
            sell_price=_dec(request.form.get("sell_price")),
            location=(request.form.get("location") or "").strip() or None,
            notes=(request.form.get("notes") or "").strip() or None,
        )
        db.session.add(item)
        db.session.flush()
        if item.quantity and item.quantity != 0:
            db.session.add(StockMovement(
                item_id=item.id,
                movement_type="in",
                quantity=item.quantity,
                balance_after=item.quantity,
                note="Opening stock",
                created_by_id=current_user.id,
                created_at=npt_now_naive(),
            ))
        db.session.commit()
        log_activity("stock_add", module="stock", record_id=item.id, details=item.name)
        flash(f"Item “{item.name}” added.", "success")
        return redirect(url_for("stock.list_items"))
    return render_template("stock/form.html", item=None, categories=categories)


@stock_bp.route("/<int:iid>/edit", methods=["GET", "POST"])
@login_required
@permission_required("stock.edit")
def edit_item(iid):
    item = db.session.get(StockItem, iid)
    if not item:
        flash("Not found.", "danger")
        return redirect(url_for("stock.list_items"))
    categories = StockCategory.query.filter_by(is_active=True).order_by(StockCategory.name).all()
    if request.method == "POST":
        item.sku = (request.form.get("sku") or "").strip() or None
        item.name = (request.form.get("name") or "").strip() or item.name
        item.category_id = request.form.get("category_id", type=int) or None
        item.unit = (request.form.get("unit") or "pcs").strip()
        item.reorder_level = _dec(request.form.get("reorder_level"))
        item.cost_price = _dec(request.form.get("cost_price"))
        item.sell_price = _dec(request.form.get("sell_price"))
        item.location = (request.form.get("location") or "").strip() or None
        item.notes = (request.form.get("notes") or "").strip() or None
        item.is_active = request.form.get("is_active") == "1"
        db.session.commit()
        flash("Item updated.", "success")
        return redirect(url_for("stock.list_items"))
    return render_template("stock/form.html", item=item, categories=categories)


@stock_bp.route("/<int:iid>/move", methods=["GET", "POST"])
@login_required
@permission_required("stock.edit")
def move_stock(iid):
    item = db.session.get(StockItem, iid)
    if not item:
        flash("Not found.", "danger")
        return redirect(url_for("stock.list_items"))
    if request.method == "POST":
        mtype = request.form.get("movement_type") or "in"
        qty = _dec(request.form.get("quantity"))
        if qty <= 0:
            flash("Quantity must be positive.", "danger")
            return redirect(url_for("stock.move_stock", iid=iid))
        bal = _dec(item.quantity)
        if mtype == "in":
            bal = bal + qty
        elif mtype == "out":
            if qty > bal:
                flash("Not enough stock.", "danger")
                return redirect(url_for("stock.move_stock", iid=iid))
            bal = bal - qty
        else:  # adjust = set absolute
            bal = qty
            qty = bal - _dec(item.quantity)
            mtype = "adjust"
        item.quantity = bal
        db.session.add(StockMovement(
            item_id=item.id,
            movement_type=mtype if mtype != "adjust" else ("in" if qty >= 0 else "out"),
            quantity=abs(qty) if mtype != "adjust" else abs(qty),
            balance_after=bal,
            reference=(request.form.get("reference") or "").strip() or None,
            note=(request.form.get("note") or "").strip() or None,
            created_by_id=current_user.id,
            created_at=npt_now_naive(),
        ))
        db.session.commit()
        log_activity("stock_move", module="stock", record_id=item.id, details=f"{mtype} {qty}")
        flash(f"Stock updated. Balance: {bal} {item.unit}", "success")
        return redirect(url_for("stock.list_items"))
    movements = (
        StockMovement.query.filter_by(item_id=item.id)
        .order_by(StockMovement.created_at.desc())
        .limit(30)
        .all()
    )
    return render_template("stock/move.html", item=item, movements=movements)


@stock_bp.route("/movements")
@login_required
@permission_required("stock.view")
def movements():
    rows = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(100).all()
    return render_template("stock/movements.html", movements=rows)


def _ensure_qr_token(item):
    import secrets
    if not item.qr_token:
        item.qr_token = secrets.token_urlsafe(16)
        db.session.commit()
    return item.qr_token


@stock_bp.route("/<int:iid>/qr")
@login_required
@permission_required("stock.view")
def item_qr(iid):
    """Printable QR for one stock item."""
    item = db.session.get(StockItem, iid)
    if not item:
        flash("Not found.", "danger")
        return redirect(url_for("stock.list_items"))
    token = _ensure_qr_token(item)
    from flask import current_app
    base = (current_app.config.get("HMS_SITE_URL") or request.url_root).rstrip("/")
    scan_url = f"{base}/stock/scan/{token}"
    return render_template("stock/qr_print.html", item=item, scan_url=scan_url, token=token)


@stock_bp.route("/scan", methods=["GET"])
@login_required
@permission_required("stock.edit")
def scan_page():
    """Camera / manual QR scan → stock IN."""
    return render_template("stock/scan.html")


@stock_bp.route("/scan/<token>", methods=["GET", "POST"])
@login_required
@permission_required("stock.edit")
def scan_qr(token):
    """Opened by QR: enter qty received → stock increases."""
    item = StockItem.query.filter_by(qr_token=token, is_active=True).first()
    if not item:
        flash("Invalid or unknown QR.", "danger")
        return redirect(url_for("stock.scan_page"))
    if request.method == "POST":
        qty = _dec(request.form.get("quantity"))
        if qty <= 0:
            flash("Enter quantity greater than 0.", "danger")
            return redirect(url_for("stock.scan_qr", token=token))
        bal = _dec(item.quantity) + qty
        item.quantity = bal
        db.session.add(StockMovement(
            item_id=item.id,
            movement_type="in",
            quantity=qty,
            balance_after=bal,
            reference=(request.form.get("reference") or "").strip() or "QR scan",
            note=(request.form.get("note") or "").strip() or "Received via QR",
            created_by_id=current_user.id,
            created_at=npt_now_naive(),
        ))
        db.session.commit()
        log_activity("stock_qr_in", module="stock", record_id=item.id, details=f"+{qty}")
        flash(f"Stock IN: {item.name} +{qty} {item.unit} → balance {bal}", "success")
        return redirect(url_for("stock.list_items"))
    return render_template("stock/scan_receive.html", item=item, token=token)
