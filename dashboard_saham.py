
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import requests

st.set_page_config(page_title="Saham Undervalued", layout="wide")

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

st.sidebar.title("📊 Pilih Saham")

default_tickers = [
    "BMRI.JK", "PTBA.JK", "BJTM.JK", "SIDO.JK",
    "BSDE.JK", "ASII.JK", "AALI.JK", "ADRO.JK",
    "BBRI.JK", "BBCA.JK", "TLKM.JK", "UNVR.JK"
]

selected = st.sidebar.multiselect(
    "📌 Pilih dari daftar umum:",
    options=sorted(default_tickers),
    default=st.session_state.get("saved_tickers", ["BBRI.JK", "BBCA.JK"])
)

query = st.sidebar.text_input("🔍 Cari saham (Yahoo Finance):")
if query:
    result = search_ticker(query)
    if result:
        st.sidebar.write("Hasil pencarian:")
        for r in result:
            st.sidebar.write(r)
    else:
        st.sidebar.warning("Tidak ditemukan.")

manual_input = st.sidebar.text_input("✍️ Tambahkan ticker manual (pisahkan dengan koma):")
if manual_input:
    manual_list = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    selected.extend(manual_list)

tickers = list(set(selected))

if st.sidebar.button("💾 Simpan Pilihan Saya"):
    st.session_state["saved_tickers"] = tickers
    st.sidebar.success("✅ Tersimpan! Gunakan kembali saat reload.")

@st.cache_data
def get_summary_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="6mo")
        price = info.get("currentPrice") or stock.history(period="1d")["Close"].iloc[-1]
        eps = info.get("trailingEps", 0)
        pbv = info.get("priceToBook", 0)
        roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None
        per = price / eps if eps else None
        fair_value = eps * 15 if eps else None
        undervalued = fair_value and price < fair_value
        return {
            "price": price, "eps": eps, "pbv": pbv, "roe": roe,
            "per": per, "fair_value": fair_value, "undervalued": undervalued,
            "hist": hist
        }
    except Exception:
        return None

data = []
for t in tickers:
    summary = get_summary_data(t)
    if summary:
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

df = pd.DataFrame(data)
st.title("📈 Dashboard Saham Undervalued")
st.dataframe(df, use_container_width=True)

# Grafik harga saham
for t in tickers:
    summary = get_summary_data(t)
    if summary and not summary["hist"].empty:
        st.subheader(f"📊 Harga Historis: {t}")
        chart = alt.Chart(summary["hist"].reset_index()).mark_line().encode(
            x="Date:T", y="Close:Q"
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
