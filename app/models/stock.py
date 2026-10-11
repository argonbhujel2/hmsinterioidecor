"""Stock / inventory for Urlabari Interior Decor materials."""
from app import db
from app.utils.timeutil import npt_now_naive


class StockCategory(db.Model):
    __tablename__ = "stock_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=npt_now_naive)

    items = db.relationship("StockItem", back_populates="category", lazy="dynamic")


class StockItem(db.Model):
    __tablename__ = "stock_items"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, index=True)
    qr_token = db.Column(db.String(64), unique=True, index=True)  # scan token
    name = db.Column(db.String(200), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("stock_categories.id"), index=True)
    unit = db.Column(db.String(30), default="pcs")  # pcs, sheet, bag, m, sqft, box
    quantity = db.Column(db.Numeric(14, 3), default=0)
    reorder_level = db.Column(db.Numeric(14, 3), default=0)
    cost_price = db.Column(db.Numeric(12, 2), default=0)
    sell_price = db.Column(db.Numeric(12, 2), default=0)
    location = db.Column(db.String(100))  # warehouse / shelf
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=npt_now_naive)
    updated_at = db.Column(db.DateTime, default=npt_now_naive, onupdate=npt_now_naive)

    category = db.relationship("StockCategory", back_populates="items")
    movements = db.relationship("StockMovement", back_populates="item", lazy="dynamic")

    @property
    def is_low(self):
        try:
            return float(self.quantity or 0) <= float(self.reorder_level or 0)
        except Exception:
            return False


class StockMovement(db.Model):
    """Stock in / out / adjust history."""
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("stock_items.id"), nullable=False, index=True)
    movement_type = db.Column(db.String(20), nullable=False)  # in, out, adjust
    quantity = db.Column(db.Numeric(14, 3), nullable=False)
    balance_after = db.Column(db.Numeric(14, 3))
    reference = db.Column(db.String(100))  # PO / job / invoice no
    note = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=npt_now_naive, index=True)

    item = db.relationship("StockItem", back_populates="movements")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
