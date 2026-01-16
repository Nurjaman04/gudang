import os

# Menentukan lokasi folder utama
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

import os

class Config:
    SECRET_KEY = 'rahasia-pergudangan'
    
    # PERBAIKAN DI SINI:
    # Kita gunakan path relative sederhana. 
    # 'sqlite:///warehouse.db' artinya: Buat file database di folder tempat kita menjalankan aplikasi (folder wms).
    SQLALCHEMY_DATABASE_URI = 'sqlite:///warehouse.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Setting Email (Biarkan saja)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')