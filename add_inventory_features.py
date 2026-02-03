import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Add unit (Satuan) to Products
    try:
        c.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT 'pcs'")
        print("Added 'unit' to products.")
    except sqlite3.OperationalError as e:
        print(f"Skipped products.unit: {e}")

    # 2. CRUD Warehouse Table (If not exists)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            type TEXT DEFAULT 'physical'
        )''')
        # Seed Main Warehouse
        c.execute("INSERT INTO warehouses (name, location, type) SELECT 'Gudang Utama', 'Pusat', 'main' WHERE NOT EXISTS (SELECT 1 FROM warehouses)")
        conn.commit()
        print("Created warehouses table.")
    except Exception as e:
        print(f"Error creating warehouses: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
