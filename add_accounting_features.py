import sqlite3
import os

def upgrade_db():
    db_path = 'instance/warehouse.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Chart of Accounts (COA)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- Asset, Liability, Equity, Revenue, Expense
            category TEXT, -- Current Asset, Fixed Asset, etc.
            balance REAL DEFAULT 0
        )''')
        print("Created accounts table.")
    except Exception as e:
        print(f"Error checking accounts table: {e}")

    # 2. Journal Entry (Header)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            reference TEXT, -- Transaction Ref
            description TEXT,
            posted_by INTEGER, -- User ID
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        print("Created journal_entries table.")
    except Exception as e:
        print(f"Error checking journal_entries table: {e}")

    # 3. Journal Items (Lines - Double Entry)
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS journal_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )''')
        print("Created journal_items table.")
    except Exception as e:
        print(f"Error checking journal_items table: {e}")

    # Seed Default COA
    coa = [
        ('1100', 'Kas & Bank', 'Asset', 'Current Asset'),
        ('1200', 'Piutang Usaha (AR)', 'Asset', 'Current Asset'),
        ('1300', 'Persediaan Barang (Inventory)', 'Asset', 'Current Asset'),
        ('2100', 'Hutang Usaha (AP)', 'Liability', 'Current Liability'),
        ('2300', 'Hutang Pajak (PPN)', 'Liability', 'Current Liability'),
        ('3100', 'Modal Disetor', 'Equity', 'Equity'),
        ('4100', 'Pendapatan Penjualan', 'Revenue', 'Revenue'),
        ('5100', 'Harga Pokok Penjualan (HPP)', 'Expense', 'Cost of Sales'),
        ('6100', 'Biaya Operasional', 'Expense', 'Expense'),
        ('9999', 'Saldo Awal (Opening Balance)', 'Equity', 'Equity') # For initial balancing
    ]

    try:
        for code, name, type_, cat in coa:
            c.execute("INSERT OR IGNORE INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)", (code, name, type_, cat))
        print("Seeded Chart of Accounts.")
    except Exception as e:
        print(f"Error seeding COA: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
