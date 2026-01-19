import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import Product, Transaction, User

app = create_app()

def seed():
    with app.app_context():
        db.drop_all()  # Reset Database
        db.create_all()
        
        print("1. Membuat Akun Admin...")
        # Password asli: 'admin123' (akan di-hash/dienkripsi)
        admin = User(
            username='admin', 
            email='admin@example.com', # Default email
            password_hash=generate_password_hash('admin123'), 
            role='admin'
        )
        db.session.add(admin)
        
        # Tambahan user lain
        staff = User(username='staff', email='staff@example.com', password_hash=generate_password_hash('staff123'), role='staff')
        manager = User(username='manager', email='manager@example.com', password_hash=generate_password_hash('manager123'), role='manager')
        
        db.session.add_all([staff, manager])

        print("2. Menambahkan Produk...")
        p1 = Product(sku="LP-001", name="Laptop Gaming ASUS", price=15000000, cost=12000000, stock_quantity=5, min_stock_threshold=5)
        p2 = Product(sku="MS-002", name="Mouse Wireless Logitech", price=250000, cost=150000, stock_quantity=50, min_stock_threshold=10)
        p3 = Product(sku="KB-003", name="Keyboard Mechanical", price=800000, cost=500000, stock_quantity=8, min_stock_threshold=10)
        
        db.session.add_all([p1, p2, p3])
        db.session.commit() # Commit dulu agar ID produk terbentuk

        print("3. Menambahkan Transaksi Palsu...")
        products = [p1, p2, p3]
        for _ in range(50):
            dipilih = random.choice(products)
            qty = random.randint(1, 3)
            days_ago = random.randint(0, 30)
            tgl_transaksi = datetime.utcnow() - timedelta(days=days_ago)

            t = Transaction(
                product_id=dipilih.id,
                transaction_type='OUT',
                quantity=qty,
                total_amount=dipilih.price * qty,
                created_at=tgl_transaksi
            )
            db.session.add(t)
        # Cari bagian loop pembuatan transaksi di seed_data.py
        print("3. Menambahkan Transaksi Palsu...")
        products = [p1, p2, p3]
        for _ in range(50):
            dipilih = random.choice(products)
            qty = random.randint(1, 3)
            days_ago = random.randint(0, 30)
            tgl_transaksi = datetime.utcnow() - timedelta(days=days_ago)
            
            # Tentukan tipe transaksi acak
            tipe = random.choice(['IN', 'OUT'])
            
            supplier_dummy = None
            ref_dummy = None
            
            if tipe == 'IN':
                supplier_dummy = "PT. Supplier Jaya"
                ref_dummy = f"SJ-{random.randint(1000,9999)}"

            t = Transaction(
                product_id=dipilih.id,
                transaction_type=tipe,
                quantity=qty,
                total_amount=dipilih.price * qty if tipe == 'OUT' else 0,
                created_at=tgl_transaksi,
                supplier=supplier_dummy, # Field baru
                reference=ref_dummy      # Field baru
            )
        db.session.commit()
        print("✅ SUKSES! Login dengan user: 'admin' dan pass: 'admin123'")

if __name__ == '__main__':
    seed()