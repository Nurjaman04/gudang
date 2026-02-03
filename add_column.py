
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        print("Attempting to add request_number column to material_requests table...")
        # SQLite syntax to add column
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE material_requests ADD COLUMN request_number VARCHAR(50)"))
            conn.commit()
        print("Column request_number added successfully.")
    except Exception as e:
        print(f"Error (might already exist): {str(e)}")
