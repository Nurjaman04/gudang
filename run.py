from app import create_app
from dotenv import load_dotenv

load_dotenv()

# Membuat aplikasi
app = create_app()

if __name__ == '__main__':
    # debug=True agar server otomatis restart saat Anda mengubah kode
    print("Server Berjalan! Buka browser di http://127.0.0.1:5000")
    app.run(debug=True, port=5000)