from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

def add_users():
    with app.app_context():
        if not User.query.filter_by(username='staff').first():
            staff = User(
                username='staff',
                email='staff@example.com',
                password_hash=generate_password_hash('staff123'),
                role='staff'
            )
            db.session.add(staff)
            print("[OK] User 'staff' berhasil ditambahkan.")
        else:
            print("[INFO] User 'staff' sudah ada.")

        if not User.query.filter_by(username='manager').first():
            manager = User(
                username='manager',
                email='manager@example.com',
                password_hash=generate_password_hash('manager123'),
                role='manager'
            )
            db.session.add(manager)
            print("[OK] User 'manager' berhasil ditambahkan.")
        else:
            print("[INFO] User 'manager' sudah ada.")
            
        db.session.commit()
        print("Selesai.")

if __name__ == '__main__':
    add_users()
