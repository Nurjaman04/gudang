import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- KONFIGURASI (Ganti dengan data asli Anda) ---
EMAIL_PENGIRIM = "email_anda@gmail.com"
EMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx" 
EMAIL_PENERIMA = "email_bos@gmail.com"

WA_PHONE = "628xxxxxxxxxx"
WA_API_KEY = "xxxxxx"

def kirim_email_low_stock(product_name, sisa_stok):
    try:
        subject = f"⚠️ PERINGATAN: Stok {product_name} Menipis!"
        body = f"Stok barang {product_name} tinggal {sisa_stok}. Segera restock!"

        msg = MIMEMultipart()
        msg['From'] = EMAIL_PENGIRIM
        msg['To'] = EMAIL_PENERIMA
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_PENGIRIM, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email terkirim.")
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