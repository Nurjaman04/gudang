import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Customers Table
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            type TEXT DEFAULT 'Personal', -- Personal, Business, Reseller
            tags TEXT, -- Comma separated
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        print("Created customers table.")
    except Exception as e:
        print(f"Error creating customers table: {e}")

    # 2. Interactions Table (CRM)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            type TEXT NOT NULL, -- Call, Visit, Email, Whatsapp, Meeting
            notes TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            follow_up_date DATE,
            status TEXT DEFAULT 'Open', -- Open, Closed
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )''')
        print("Created interactions table.")
    except Exception as e:
        print(f"Error creating interactions table: {e}")

    # 3. Add customer_id to Transactions
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN customer_id INTEGER")
        print("Added customer_id to transactions.")
    except sqlite3.OperationalError:
        print("transactions.customer_id already exists.")

    # 4. Seed Customers from existing Sales History
    try:
        # Get distinct 'supplier' names from OUT transactions (Sales)
        c.execute("SELECT DISTINCT supplier FROM transactions WHERE transaction_type = 'OUT' AND supplier IS NOT NULL AND supplier != ''")
        existing_names = c.fetchall()
        
        count = 0
        for row in existing_names:
            name = row[0]
            # Check if exists
            c.execute("SELECT id FROM customers WHERE name = ?", (name,))
            if not c.fetchone():
                c.execute("INSERT INTO customers (name, type) VALUES (?, 'Imported')", (name,))
                count += 1
        
        print(f"Imported {count} customers from transaction history.")
        
        # Link Transactions to new Customers
        c.execute("SELECT id, name FROM customers")
        customers = c.fetchall()
        for cust_id, cust_name in customers:
            c.execute("UPDATE transactions SET customer_id = ? WHERE supplier = ? AND transaction_type = 'OUT'", (cust_id, cust_name))
            
    except Exception as e:
        print(f"Error seeding customers: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
