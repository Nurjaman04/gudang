import matplotlib
matplotlib.use('Agg') # Backend non-GUI (Wajib untuk Web Server)
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

def calculate_revenue_stats(transactions_data):
    """
    Menghitung statistik dasar dari list transaksi (dict).
    """
    if not transactions_data:
        return {"total_revenue": 0, "total_items_sold": 0}

    df = pd.DataFrame(transactions_data)
    
    stats = {
        "total_revenue": df['total_amount'].sum(),
        "total_items_sold": df['quantity'].sum(),
        "average_order_value": df['total_amount'].mean()
    }
    return stats

def generate_sales_chart(transactions_data):
    """
    Membuat grafik batang penjualan per tanggal.
    Output: String Base64 (bisa langsung dipasang di tag <img src='...'>)
    """
    if not transactions_data:
        return None

    # 1. Konversi data ke Pandas DataFrame
    df = pd.DataFrame(transactions_data)
    
    # 2. Pastikan kolom tanggal adalah datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # 3. Agregasi: Total penjualan per Tanggal
    daily_sales = df.groupby(df['date'].dt.date)['total_amount'].sum()

    # 4. Membuat Plot
    plt.figure(figsize=(10, 5)) # Ukuran gambar
    daily_sales.plot(kind='bar', color='#4CAF50') # Warna hijau
    
    plt.title('Tren Penjualan Harian')
    plt.xlabel('Tanggal')
    plt.ylabel('Pendapatan (Rp)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 5. Simpan ke Buffer (Memory), bukan file
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close() # Tutup plot agar memori tidak bocor

    # 6. Encode ke Base64
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    
    return f"data:image/png;base64,{plot_url}"