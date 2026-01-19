import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os

# --- KONFIGURASI (Diambil dari Environment Variables) ---
EMAIL_PENGIRIM = os.environ.get('EMAIL_USER', "email_anda@gmail.com")
EMAIL_APP_PASSWORD = os.environ.get('EMAIL_PASS', "xxxx xxxx xxxx xxxx")
EMAIL_PENERIMA = os.environ.get('EMAIL_RECEIVER', "email_bos@gmail.com")

WA_PHONE = os.environ.get('WA_PHONE', "628xxxxxxxxxx")
WA_API_KEY = os.environ.get('WA_API_KEY', "xxxxxx")

def kirim_email_low_stock(product_name, sisa_stok, recipients=None):
    # Cek apakah email sudah dikonfigurasi
    if "email_anda" in EMAIL_PENGIRIM or "xxxx" in EMAIL_APP_PASSWORD:
        print("⚠️  Email belum dikonfigurasi. Lewati pengiriman email.")
        return

    # Tentukan penerima
    target_emails = recipients if recipients else [EMAIL_PENERIMA]
    
    if not target_emails:
        print("⚠️ Tidak ada penerima email yang valid.")
        return

    try:
        # Gunakan SMTP_SSL untuk port 465
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_PENGIRIM, EMAIL_APP_PASSWORD)

        # Kirim email satu per satu agar header 'To' sesuai dengan penerima
        for email_tujuan in target_emails:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_PENGIRIM
            msg['To'] = email_tujuan
            msg['Subject'] = f"⚠️ PERINGATAN: Stok {product_name} Menipis!"
            
            body = f"Halo,\n\nStok barang {product_name} saat ini tinggal {sisa_stok}. Segera lakukan restock.\n\nSalam,\nSistem Gudang"
            msg.attach(MIMEText(body, 'plain'))
            
            server.send_message(msg)
            print(f"✅ Email terkirim ke: {email_tujuan}")

        server.quit()
        
    except Exception as e:
        print(f"❌ Gagal kirim email: {e}")

def kirim_wa_low_stock(product_name, sisa_stok):
    try:
        pesan = f"⚠️ *PERINGATAN STOK*%0A%0ABarang: {product_name}%0ASisa: {sisa_stok}"
        url = f"https://api.callmebot.com/whatsapp.php?phone={WA_PHONE}&text={pesan}&apikey={WA_API_KEY}"
        requests.get(url)
        print("✅ WA terkirim.")
    except Exception as e:
        print(f"❌ Gagal kirim WA: {e}")