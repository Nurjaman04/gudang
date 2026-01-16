import sqlite3

def migrate():
    print("Migrating database...")
    try:
        # Connect to your SQLite database
        # Adjust the path if your instance folder is elsewhere
        conn = sqlite3.connect(r'c:\Users\Lenovo\Documents\wms\instance\warehouse.db') 
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'email' not in columns:
            print("Adding 'email' column to 'users' table...")
            # Add column as nullable first (to handle existing rows), or with default
            # SQLite limitations on ALTER TABLE ADD COLUMN NON NULL
            # We'll add it as TEXT first.
            cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(120)")
            conn.commit()
            print("Migration successful: 'email' column added.")
        else:
            print("'email' column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")
        # Fallback for dev: maybe the db is in the app root?
        try:
             conn = sqlite3.connect(r'c:\Users\Lenovo\Documents\wms\wms.db')
             cursor = conn.cursor()
             cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(120)")
             conn.commit()
             conn.close()
             print("Migration successful (root db).")
        except:
            pass

if __name__ == "__main__":
    migrate()
