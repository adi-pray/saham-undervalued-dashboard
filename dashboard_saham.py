import requests
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

            # --- Rekomendasi beli/jual/netral ---
rekom = "⚖️ Tahan"
if summary["undervalued"] and summary["per"] and summary["pbv"] and summary["roe"]:
    if summary["per"] < 15 and summary["pbv"] < 1.5 and summary["roe"] > 10:
        rekom = "🟢 Beli"
elif summary["per"] and summary["per"] > 20 and summary["price"] > summary["fair_value"]:
    rekom = "🔴 Jual"

data.append({
    "Ticker": t,
    "Harga": summary["price"],
    "EPS": summary["eps"],
    "PER": summary["per"],
    "PBV": summary["pbv"],
    "ROE (%)": summary["roe"],
    "Fair Value": summary["fair_value"],
    "Undervalued": "✅" if summary["undervalued"] else "❌",
    "Rekomendasi": rekom
})

        except Exception as e:
            st.warning(f"Gagal ambil data {ticker}: {e}")
    return pd.DataFrame(data)

# --- Sidebar ---
# --- Fungsi untuk cari ticker dari Yahoo Finance Search API ---
@st.cache_data(ttl=86400)
def search_ticker(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=en-US"
    try:
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    results = data.get("quotes", [])
    return [f"{item['symbol']} - {item['shortname']}" for item in results if "symbol" in item]
except Exception as e:
    return []


# --- Sidebar Input ---
st.sidebar.title("📊 Pilih Saham")

# ✅ Default tickers saham lokal
default_tickers = [
    "BMRI.JK", "PTBA.JK", "BJTM.JK", "SIDO.JK",
    "BSDE.JK", "ASII.JK", "AALI.JK", "ADRO.JK",
    "BBRI.JK", "BBCA.JK", "TLKM.JK", "UNVR.JK"
]

# Bagian 1: Dropdown statis
selected = st.sidebar.multiselect(
    "📌 Pilih dari daftar umum:",
    options=sorted(default_tickers),
    default=st.session_state.get("saved_tickers", ["BBRI.JK", "BBCA.JK"])
)

# Bagian 2: Pencarian dinamis pakai API
query = st.sidebar.text_input("🔍 Cari saham (Yahoo Finance):")
if query:
    result = search_ticker(query)
    if result:
        st.sidebar.write("Hasil pencarian:")
        for r in result:
            st.sidebar.write(r)
    else:
        st.sidebar.warning("Tidak ditemukan.")

# Bagian 3: Input manual
manual_input = st.sidebar.text_input("✍️ Tambahkan ticker manual (pisahkan dengan koma):")
if manual_input:
    manual_list = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    selected.extend(manual_list)

# Hapus duplikat
tickers = list(set(selected))

# Tombol simpan pilihan
if st.sidebar.button("💾 Simpan Pilihan Saya"):
    st.session_state["saved_tickers"] = tickers
    st.sidebar.success("✅ Tersimpan! Gunakan kembali saat reload.")


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

