import sqlite3
import os

def migrate():
    print("Migrating database for features...")
    
    # List of possible database paths
    db_paths = [
        r'c:\Users\Lenovo\Documents\wms\instance\warehouse.db',
        r'c:\Users\Lenovo\Documents\wms\wms.db',
        os.path.join(os.getcwd(), 'instance', 'warehouse.db'),
        os.path.join(os.getcwd(), 'wms.db')
    ]
    
    migrated = False

    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"Checking database at: {db_path}")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if column exists
                cursor.execute("PRAGMA table_info(users)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if 'features' not in columns:
                    print(f"Adding 'features' column to 'users' table in {db_path}...")
                    cursor.execute("ALTER TABLE users ADD COLUMN features TEXT")
                    conn.commit()
                    print("Migration successful.")
                    migrated = True
                else:
                    print(f"'features' column already exists in {db_path}.")
                    migrated = True
                    
                conn.close()
            except Exception as e:
                print(f"Migration failed for {db_path}: {e}")
    
    if not migrated:
        print("Warning: No database found or migrated.")

if __name__ == "__main__":
    migrate()
