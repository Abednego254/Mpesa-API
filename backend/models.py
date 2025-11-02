from datetime import datetime
from backend.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="seller")
    password_hash = db.Column(db.String(256), nullable=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)

    # Relationship — one seller can have many invoices
    invoices = db.relationship("Invoice", backref="seller", lazy=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    photo = db.Column(db.String(255))  # <-- new column
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice_items = db.relationship("InvoiceItem", backref="item", lazy=True)

    def __repr__(self):
        return f"<Item {self.name} - {self.price}>"



class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # seller id
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    checkout_request_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    transaction_date = db.Column(db.String(20), nullable=True)

    items = db.relationship("InvoiceItem", backref="invoice", lazy=True)
    mpesa_callbacks = db.relationship("MpesaCallback", backref="invoice", lazy=True)

    def __repr__(self):
        return f"<Invoice {self.id} - Seller {self.user_id} - Total {self.total}>"


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<InvoiceItem invoice={self.invoice_id}, item={self.item_id}, qty={self.quantity}>"


class MpesaCallback(db.Model):
    __tablename__ = "mpesa_callbacks"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    merchant_request_id = db.Column(db.String(100))
    checkout_request_id = db.Column(db.String(100))
    result_code = db.Column(db.Integer)
    result_desc = db.Column(db.String(255))
    amount = db.Column(db.Float)
    mpesa_receipt_number = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    transaction_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MpesaCallback invoice={self.invoice_id}, result={self.result_code}>"

class Commission(db.Model):
    __tablename__ = "commissions"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False, default=0.30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    seller = db.relationship("User", backref="commissions", lazy=True)
    invoice = db.relationship("Invoice", backref="commission", lazy=True)

    def __repr__(self):
        return f"<Commission seller={self.seller_id}, invoice={self.invoice_id}, amount={self.amount}>"
