import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Suppliers Table
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            contact_person TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        print("Created suppliers table.")
        
        # Seed from existing transactions
        c.execute("SELECT DISTINCT supplier FROM transactions WHERE transaction_type = 'IN' AND supplier IS NOT NULL AND supplier != ''")
        existing_suppliers = c.fetchall()
        for row in existing_suppliers:
            name = row[0]
            c.execute("SELECT id FROM suppliers WHERE name = ?", (name,))
            if not c.fetchone():
                c.execute("INSERT INTO suppliers (name) VALUES (?)", (name,))
        print(f"Seeded {len(existing_suppliers)} suppliers from history.")
        
    except Exception as e:
        print(f"Error creating suppliers table: {e}")

    # 2. Purchase Requests (PR)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pr_number TEXT NOT NULL UNIQUE, -- PR-YYYYMM-XXXX
            requested_by INTEGER, -- User ID
            date DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'Pending', -- Pending, Approved, Rejected, PO Created
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_request_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_request_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(purchase_request_id) REFERENCES purchase_requests(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )''')
        print("Created purchase_requests tables.")
    except Exception as e:
        print(f"Error creating PR tables: {e}")

    # 3. Purchase Orders (PO)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT NOT NULL UNIQUE, -- PO-YYYYMM-XXXX
            supplier_id INTEGER NOT NULL,
            purchase_request_id INTEGER, -- Link back to PR
            date DATE DEFAULT CURRENT_DATE,
            expected_date DATE,
            status TEXT DEFAULT 'Draft', -- Draft, Sent, Partial, Received, Cancelled
            total_amount REAL DEFAULT 0,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(purchase_request_id) REFERENCES purchase_requests(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            subtotal REAL NOT NULL,
            received_qty INTEGER DEFAULT 0,
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )''')
        print("Created purchase_orders tables.")
    except Exception as e:
        print(f"Error creating PO tables: {e}")
        
    # 4. Purchase Returns
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_number TEXT NOT NULL UNIQUE,
            purchase_order_id INTEGER NOT NULL,
            date DATE DEFAULT CURRENT_DATE,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(id)
        )''')
        print("Created purchase_returns table.")
    except Exception as e:
        print(f"Error creating purchase_returns table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
