import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Categories
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )''')
        # Seed default categories
        defaults = ['General', 'Electronics', 'Raw Material', 'Finished Goods']
        for d in defaults:
            try:
                c.execute("INSERT INTO categories (name) VALUES (?)", (d,))
            except sqlite3.IntegrityError:
                pass
        print("Created categories table.")
    except Exception as e:
        print(f"Error creating categories table: {e}")

    # 2. Units
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE, -- e.g., Pcs, Kg, Box
            description TEXT
        )''')
        # Seed default units
        defaults = ['Pcs', 'Kg', 'Ltr', 'Box', 'Rim', 'Set']
        for d in defaults:
            try:
                c.execute("INSERT INTO units (name) VALUES (?)", (d,))
            except sqlite3.IntegrityError:
                pass
        print("Created units table.")
    except Exception as e:
        print(f"Error creating units table: {e}")

    # 3. Inventory Stock (Per Warehouse Stock)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS inventory_stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 0,
            location_rack TEXT, -- Specific rack in that warehouse
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
            UNIQUE(product_id, warehouse_id)
        )''')
        print("Created inventory_stocks table.")

        # Seed initial Main Warehouse
        c.execute("INSERT INTO warehouses (name, type) SELECT 'Gudang Utama', 'main' WHERE NOT EXISTS (SELECT 1 FROM warehouses WHERE type='main')")
        
        # Migrate existing global stock to Main Warehouse
        # Get Main Warehouse ID
        c.execute("SELECT id FROM warehouses WHERE type='main' LIMIT 1")
        main_wh_id_row = c.fetchone()
        if main_wh_id_row:
            main_wh_id = main_wh_id_row[0]
            
            # Insert stocks
            c.execute(f'''
                INSERT OR IGNORE INTO inventory_stocks (product_id, warehouse_id, quantity)
                SELECT id, {main_wh_id}, stock_quantity FROM products
            ''')
            print("Migrated global stock to Gudang Utama.")
            
    except Exception as e:
        print(f"Error creating inventory_stocks table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
