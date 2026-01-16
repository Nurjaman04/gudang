import os

# Menentukan lokasi folder utama
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

import os

class Config:
    SECRET_KEY = 'rahasia-pergudangan'
    
    # Konfigurasi Database
    # Cek apakah berjalan di lingkungan Lambda/Netlify (Read-Only)
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        # Gunakan /tmp yang writable di lingkungan serverless
        SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/warehouse.db'
    else:
        # Gunakan path lokal untuk development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///warehouse.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Setting Email (Biarkan saja)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')