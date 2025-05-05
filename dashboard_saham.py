import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Saham Undervalued", layout="wide")

# --- Fungsi untuk ambil data dan hitung fair value ---
@st.cache_data(ttl=3600)
def load_data(tickers):
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice")
            eps = info.get("trailingEps", 0)
            fair_value = eps * 15 if eps else 0
            undervalued = price < fair_value * 0.8 if fair_value else False

            data.append({
                "Ticker": ticker,
                "Price": price,
                "EPS": eps,
                "Fair Value (Est.)": round(fair_value, 2),
                "Undervalued": undervalued
            })
        except Exception as e:
            st.warning(f"Gagal ambil data {ticker}: {e}")
    return pd.DataFrame(data)

# --- Sidebar ---
st.sidebar.title("Pengaturan")
# Contoh daftar ticker populer (bisa diganti/ditambah)
default_tickers = [
    "BMRI.JK", "PTBA.JK", "BJTM.JK", "SIDO.JK", "BSDE.JK", "ASII.JK", "AALI.JK", "ADRO.JK",
    "BBRI.JK", "BBCA.JK", "TLKM.JK", "UNVR.JK"
]

tickers = st.sidebar.multiselect(
    "Pilih saham yang ingin dianalisis:",
    options=sorted(default_tickers),
    default=["BMRI.JK", "PTBA.JK", "BJTM.JK"]
)

# Tambahan input manual juga (opsional)
manual_input = st.sidebar.text_input("Atau masukkan kode ticker tambahan (pisahkan dengan koma):", "")
if manual_input:
    manual_list = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    tickers.extend(manual_list)
    tickers = list(set(tickers))  # hilangkan duplikat

refresh = st.sidebar.button("🔄 Refresh Data")

# --- Load dan tampilkan data ---
if tickers:
    df = load_data(tickers)

    st.title("📈 Dashboard Saham Undervalued")
    st.caption("Prediksi fair value berdasarkan EPS x 15. Saham dianggap undervalued jika harga saat ini < 80% dari fair value.")

    st.dataframe(df, use_container_width=True)

    undervalued_df = df[df["Undervalued"] == True]
    st.subheader("📉 Saham yang Teridentifikasi *Undervalued*")
    st.dataframe(undervalued_df, use_container_width=True)

else:
    st.warning("Masukkan setidaknya satu ticker saham.")

