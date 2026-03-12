import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import requests

st.set_page_config(page_title="Saham Undervalued", layout="wide")

# =========================
# Helpers
# =========================
@st.cache_data(ttl=86400)
def search_ticker(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=en-US"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        results = data.get("quotes", [])
        return [
            {
                "label": f"{item.get('symbol', '')} - {item.get('shortname', item.get('longname', ''))}",
                "symbol": item.get("symbol", "")
            }
            for item in results
            if item.get("symbol")
        ]
    except Exception:
        return []

@st.cache_data(ttl=3600)
def get_summary_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        hist = stock.history(period="6mo", auto_adjust=False)

        if hist.empty:
            return None

        price = info.get("currentPrice")
        if price is None:
            price = hist["Close"].dropna().iloc[-1] if not hist["Close"].dropna().empty else None

        eps = info.get("trailingEps")
        pbv = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        roe = roe_raw * 100 if roe_raw is not None else None

        # PER hanya valid jika EPS positif
        per = (price / eps) if (price is not None and eps is not None and eps > 0) else None

        # Fair value sederhana: EPS x 15, hanya jika EPS positif
        fair_value = (eps * 15) if (eps is not None and eps > 0) else None

        undervalued = (
            price is not None and
            fair_value is not None and
            price < fair_value
        )

        return {
            "price": price,
            "eps": eps,
            "pbv": pbv,
            "roe": roe,
            "per": per,
            "fair_value": fair_value,
            "undervalued": undervalued,
            "hist": hist
        }
    except Exception:
        return None

def classify_recommendation(summary):
    price = summary.get("price")
    per = summary.get("per")
    pbv = summary.get("pbv")
    roe = summary.get("roe")
    fair_value = summary.get("fair_value")
    undervalued = summary.get("undervalued")

    if (
        undervalued
        and per is not None and per < 15
        and pbv is not None and pbv < 1.5
        and roe is not None and roe > 10
    ):
        return "🟢 Beli"

    if (
        per is not None and per > 20
        and fair_value is not None
        and price is not None
        and price > fair_value
    ):
        return "🔴 Jual"

    return "⚖️ Tahan"

# =========================
# Sidebar
# =========================
st.sidebar.title("📊 Pilih Saham")

default_tickers = [
    "BMRI.JK", "PTBA.JK", "BJTM.JK", "SIDO.JK",
    "BSDE.JK", "ASII.JK", "AALI.JK", "ADRO.JK",
    "BBRI.JK", "BBCA.JK", "TLKM.JK", "UNVR.JK"
]

if "saved_tickers" not in st.session_state:
    st.session_state["saved_tickers"] = ["BBRI.JK", "BBCA.JK"]

selected = st.sidebar.multiselect(
    "📌 Pilih dari daftar umum:",
    options=sorted(default_tickers),
    default=st.session_state["saved_tickers"]
)

query = st.sidebar.text_input("🔍 Cari saham (Yahoo Finance):")
search_results = []

if query:
    search_results = search_ticker(query)
    if search_results:
        selected_search = st.sidebar.multiselect(
            "Hasil pencarian:",
            options=[item["symbol"] for item in search_results],
            format_func=lambda x: next(
                (item["label"] for item in search_results if item["symbol"] == x), x
            )
        )
        selected.extend(selected_search)
    else:
        st.sidebar.warning("Tidak ditemukan.")

manual_input = st.sidebar.text_input("✍️ Tambahkan ticker manual (pisahkan dengan koma):")
if manual_input:
    manual_list = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    selected.extend(manual_list)

tickers = sorted(list(set(selected)))

if st.sidebar.button("💾 Simpan Pilihan Saya"):
    st.session_state["saved_tickers"] = tickers
    st.sidebar.success("✅ Tersimpan! Gunakan kembali saat reload.")

# =========================
# Main content
# =========================
st.title("📈 Dashboard Saham Undervalued")

data = []
for t in tickers:
    summary = get_summary_data(t)
    if summary:
        data.append({
            "Ticker": t,
            "Harga": summary["price"],
            "EPS": summary["eps"],
            "PER": summary["per"],
            "PBV": summary["pbv"],
            "ROE (%)": summary["roe"],
            "Fair Value": summary["fair_value"],
            "Undervalued": "✅" if summary["undervalued"] else "❌",
            "Rekomendasi": classify_recommendation(summary)
        })

df = pd.DataFrame(data)

if df.empty:
    st.info("Belum ada data yang bisa ditampilkan.")
else:
    st.dataframe(df, use_container_width=True)

# Grafik harga saham
for t in tickers:
    summary = get_summary_data(t)
    if summary and not summary["hist"].empty:
        st.subheader(f"📊 Harga Historis: {t}")
        hist_df = summary["hist"].reset_index()[["Date", "Close"]]

        chart = (
            alt.Chart(hist_df)
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Tanggal"),
                y=alt.Y("Close:Q", title="Harga Penutupan"),
                tooltip=["Date:T", "Close:Q"]
            )
            .properties(height=300)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
