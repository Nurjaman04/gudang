from datetime import datetime
from app import db
# --- Tabel Warehouse (Multi Gudang) ---
class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=True)
    type = db.Column(db.String(50), default='physical') # main, branch, virtual
    
    stocks = db.relationship('InventoryStock', backref='warehouse', lazy=True)

    def __repr__(self):
        return f"<Warehouse {self.name}>"

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

class Unit(db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

class InventoryStock(db.Model):
    __tablename__ = 'inventory_stocks'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    location_rack = db.Column(db.String(100)) # Rack location in this specific warehouse
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = db.relationship('Product', backref='stocks')

# --- Accounting Models ---
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False) # Asset, Liability, Equity, Revenue, Expense
    category = db.Column(db.String(50), nullable=True) # Current Asset, etc.
    balance = db.Column(db.Float, default=0)

    def __repr__(self):
        return f"<{self.code} - {self.name}>"

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    reference = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('JournalItem', backref='journal_entry', lazy=True, cascade="all, delete-orphan")

class JournalItem(db.Model):
    __tablename__ = 'journal_items'
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit = db.Column(db.Float, default=0)
    credit = db.Column(db.Float, default=0)
    
    account = db.relationship('Account', backref='journal_items')

# --- CRM Models ---
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), default='Personal') # Personal, Business, Reseller
    tags = db.Column(db.Text, nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    interactions = db.relationship('Interaction', backref='customer', lazy=True)
    transactions = db.relationship('Transaction', backref='customer', lazy=True)

class Interaction(db.Model):
    __tablename__ = 'interactions'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False) # Call, Visit, Email
    notes = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Open')

# --- Sales Models ---
class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Draft') # Draft, Confirmed, Paid, Cancelled
    total_amount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    grand_total = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('SalesOrderItem', backref='sales_order', lazy=True, cascade="all, delete-orphan")
    customer_rel = db.relationship('Customer', backref='sales_orders')
    
class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'
    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product')

class SalesReturn(db.Model):
    __tablename__ = 'sales_returns'
    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=True)
    total_refund = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales_order = db.relationship('SalesOrder', backref='returns')

# --- Purchasing Models ---
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'
    id = db.Column(db.Integer, primary_key=True)
    pr_number = db.Column(db.String(50), unique=True, nullable=False)
    requested_by = db.Column(db.Integer, nullable=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected, PO Created
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('PurchaseRequestItem', backref='purchase_request', lazy=True, cascade="all, delete-orphan")

class PurchaseRequestItem(db.Model):
    __tablename__ = 'purchase_request_items'
    id = db.Column(db.Integer, primary_key=True)
    purchase_request_id = db.Column(db.Integer, db.ForeignKey('purchase_requests.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    product = db.relationship('Product')

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    purchase_request_id = db.Column(db.Integer, db.ForeignKey('purchase_requests.id'), nullable=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    expected_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Draft') # Draft, Sent, Received, Cancelled
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade="all, delete-orphan")
    returns = db.relationship('PurchaseReturn', backref='purchase_order', lazy=True)

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    received_qty = db.Column(db.Integer, default=0)
    
    product = db.relationship('Product')

class PurchaseReturn(db.Model):
    __tablename__ = 'purchase_returns'
    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    
    # Smart Inventory Fields
    lead_time_days = db.Column(db.Integer, default=3) # Needed for dynamic reorder
    category = db.Column(db.String(50), default='General') # For segregation
    unit = db.Column(db.String(20), default='pcs') # Satuan Barang (pcs, kg, box, ltr)
    rack_location = db.Column(db.String(50), default='Rak A-01') # New: Warehouse Layout
    
    transactions = db.relationship('Transaction', backref='product', lazy=True)
    batches = db.relationship('Batch', backref='product', lazy=True)

    def __repr__(self):
        return f"<Product {self.sku}>"

# --- Tabel Batch (Smart Inventory Engine) ---
class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False) # e.g., INV-20231024-001
    initial_quantity = db.Column(db.Integer, nullable=False)
    current_quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False) # For FIFO Valuation
    expiry_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Batch {self.batch_number} - {self.current_quantity}>"

# --- Tabel Detail Transaksi Batch (Audit Trail) ---
class BatchTransaction(db.Model):
    __tablename__ = 'batch_transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    


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
    branch_name = db.Column(db.String(100), nullable=True) # New Branch Field
    fulfillment_status = db.Column(db.String(20), default='completed') # pending, picked, packed, shipped
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True) # New CRM Link

    def __repr__(self):
        return f"<Transaction {self.transaction_type}>"

# --- Tabel Material Request (Permintaan Barang Antar Cabang) ---
class MaterialRequest(db.Model):
    __tablename__ = 'material_requests'
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(50), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    branch_name = db.Column(db.String(100), nullable=False) # Cabang Tujuan Request (Dari mana barang diminta)
    status = db.Column(db.String(20), default='PENDING') # PENDING, PROCESSED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='material_requests')

    def __repr__(self):
        return f"<MaterialRequest {self.branch_name} - {self.product.name}>"

# --- Tabel User ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # New Email Field
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='staff')
    features = db.Column(db.Text, nullable=True) # JSON string or comma-separated list of allowed features

    def __repr__(self):
        return f"<User {self.username}>"