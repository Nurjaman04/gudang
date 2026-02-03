import sqlite3
import os

def check_db():
    db_path = 'wms.db'
    print(f"Checking DB at: {os.path.abspath(db_path)}")
    
    if not os.path.exists(db_path):
        print("DB file does not exist!")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # List tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("Tables found:", tables)
    
    conn.close()

if __name__ == "__main__":
    check_db()
