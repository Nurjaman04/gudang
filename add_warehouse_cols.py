import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Add rack_location to Products
    try:
        c.execute("ALTER TABLE products ADD COLUMN rack_location TEXT DEFAULT 'Rak A-01'")
        print("Added rack_location to products.")
    except sqlite3.OperationalError as e:
        print(f"Skipped products.rack_location: {e}")

    # 2. Add fulfillment_status to Transactions
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN fulfillment_status TEXT DEFAULT 'completed'")
        print("Added fulfillment_status to transactions.")
    except sqlite3.OperationalError as e:
        print(f"Skipped transactions.fulfillment_status: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
