import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Sales Order Header
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE, -- SO-YYYYMM-XXXX
            customer_id INTEGER,
            date DATE DEFAULT CURRENT_DATE,
            due_date DATE,
            status TEXT DEFAULT 'Draft', -- Draft, Confirmed, Paid, Cancelled
            total_amount REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            grand_total REAL DEFAULT 0,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )''')
        print("Created sales_orders table.")
    except Exception as e:
        print(f"Error creating sales_orders table: {e}")

    # 2. Sales Order Items (Lines)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS sales_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL, -- Unit Price at time of sale
            subtotal REAL NOT NULL,
            FOREIGN KEY(sales_order_id) REFERENCES sales_orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )''')
        print("Created sales_order_items table.")
    except Exception as e:
        print(f"Error creating sales_order_items table: {e}")

    # 3. Sales Returns (Retur Penjualan)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS sales_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_number TEXT NOT NULL UNIQUE, -- RET-YYYYMM-XXXX
            sales_order_id INTEGER NOT NULL,
            date DATE DEFAULT CURRENT_DATE,
            reason TEXT,
            total_refund REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending', -- Pending, Approved
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sales_order_id) REFERENCES sales_orders(id)
        )''')
        print("Created sales_returns table.")
    except Exception as e:
        print(f"Error creating sales_returns table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
