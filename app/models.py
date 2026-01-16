from datetime import datetime
from app import db

# --- Tabel Produk ---
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_threshold = db.Column(db.Integer, default=10)
    transactions = db.relationship('Transaction', backref='product', lazy=True)

    def __repr__(self):
        return f"<Product {self.sku}>"

# --- Tabel Transaksi (HANYA BOLEH ADA 1 KALI) ---
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Kolom Baru
    supplier = db.Column(db.String(100), nullable=True)
    reference = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Transaction {self.transaction_type}>"

# --- Tabel User ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # New Email Field
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='staff')

    def __repr__(self):
        return f"<User {self.username}>"