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
    headers = {"User-Agent": "Mozilla/5.0"}
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
            close_series = hist["Close"].dropna()
            price = close_series.iloc[-1] if not close_series.empty else None

        eps = info.get("trailingEps")
        pbv = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        roe = roe_raw * 100 if roe_raw is not None else None

        per = (price / eps) if (price is not None and eps is not None and eps > 0) else None
        fair_value = (eps * 15) if (eps is not None and eps > 0) else None

        undervalued = (
            price is not None and
            fair_value is not None and
            price < fair_value
        )

        upside_pct = (
            ((fair_value - price) / price) * 100
            if price is not None and fair_value is not None and price > 0
            else None
        )

        return {
            "price": price,
            "eps": eps,
            "pbv": pbv,
            "roe": roe,
            "per": per,
            "fair_value": fair_value,
            "undervalued": undervalued,
            "upside_pct": upside_pct,
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

def calculate_score(summary):
    """
    Score sederhana untuk ranking.
    Semakin tinggi semakin menarik.
    """
    score = 0

    per = summary.get("per")
    pbv = summary.get("pbv")
    roe = summary.get("roe")
    upside_pct = summary.get("upside_pct")
    undervalued = summary.get("undervalued")

    if undervalued:
        score += 30

    if per is not None:
        if per < 10:
            score += 25
        elif per < 15:
            score += 18
        elif per < 20:
            score += 8

    if pbv is not None:
        if pbv < 1:
            score += 20
        elif pbv < 1.5:
            score += 12
        elif pbv < 2:
            score += 5

    if roe is not None:
        if roe > 20:
            score += 25
        elif roe > 15:
            score += 18
        elif roe > 10:
            score += 10

    if upside_pct is not None:
        if upside_pct > 50:
            score += 20
        elif upside_pct > 30:
            score += 12
        elif upside_pct > 15:
            score += 6

    return score

def style_recommendation(val):
    if "Beli" in str(val):
        return "background-color: #d4edda; color: #155724; font-weight: bold;"
    if "Jual" in str(val):
        return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
    return "background-color: #fff3cd; color: #856404; font-weight: bold;"

def format_number(v, digits=2):
    if v is None or pd.isna(v):
        return "-"
    return f"{v:,.{digits}f}"

# =========================
# Sidebar
# =========================
st.sidebar.title("📊 Pilih Saham")

default_tickers = [
    "BMRI.JK", "PTBA.JK", "BJTM.JK", "SIDO.JK",
    "BSDE.JK", "ASII.JK", "AALI.JK", "ADRO.JK",
    "BBRI.JK", "BBCA.JK", "TLKM.JK", "UNVR.JK",
]

if "saved_tickers" not in st.session_state:
    st.session_state["saved_tickers"] = ["BBRI.JK", "BBCA.JK"]

selected = st.sidebar.multiselect(
    "📌 Pilih dari daftar umum:",
    options=sorted(default_tickers),
    default=st.session_state["saved_tickers"]
)

query = st.sidebar.text_input("🔍 Cari saham (Yahoo Finance)")
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

manual_input = st.sidebar.text_input("✍️ Tambahkan ticker manual (pisahkan koma)")
if manual_input:
    manual_list = [t.strip().upper() for t in manual_input.split(",") if t.strip()]
    selected.extend(manual_list)

tickers = sorted(list(set(selected)))

if st.sidebar.button("💾 Simpan Pilihan Saya"):
    st.session_state["saved_tickers"] = tickers
    st.sidebar.success("✅ Tersimpan!")

st.sidebar.markdown("---")
show_only_undervalued = st.sidebar.checkbox("Tampilkan hanya undervalued", value=False)
show_charts = st.sidebar.checkbox("Tampilkan chart historis per saham", value=True)
show_comparison_chart = st.sidebar.checkbox("Tampilkan chart perbandingan", value=True)

# =========================
# Data Collection
# =========================
rows = []
histories = []

for t in tickers:
    summary = get_summary_data(t)
    if summary:
        rekom = classify_recommendation(summary)
        score = calculate_score(summary)

        rows.append({
            "Ticker": t,
            "Harga": summary["price"],
            "EPS": summary["eps"],
            "PER": summary["per"],
            "PBV": summary["pbv"],
            "ROE (%)": summary["roe"],
            "Fair Value": summary["fair_value"],
            "Upside (%)": summary["upside_pct"],
            "Undervalued": "✅" if summary["undervalued"] else "❌",
            "Rekomendasi": rekom,
            "Score": score
        })

        hist = summary["hist"].copy().reset_index()
        if not hist.empty:
            base_price = hist["Close"].iloc[0]
            if pd.notna(base_price) and base_price != 0:
                hist["Indexed"] = (hist["Close"] / base_price) * 100
                hist["Ticker"] = t
                histories.append(hist[["Date", "Ticker", "Close", "Indexed"]])

df = pd.DataFrame(rows)

if df.empty:
    st.title("📈 Dashboard Saham Undervalued")
    st.info("Belum ada data yang bisa ditampilkan.")
    st.stop()

# Filter undervalued
if show_only_undervalued:
    df = df[df["Undervalued"] == "✅"].copy()

# Sort ranking
df = df.sort_values(by=["Score", "Upside (%)"], ascending=[False, False], na_position="last").reset_index(drop=True)

# =========================
# Header
# =========================
st.title("📈 Dashboard Saham Undervalued")

col1, col2, col3, col4 = st.columns(4)

total_saham = len(df)
jumlah_beli = (df["Rekomendasi"] == "🟢 Beli").sum()
jumlah_tahan = (df["Rekomendasi"] == "⚖️ Tahan").sum()
jumlah_jual = (df["Rekomendasi"] == "🔴 Jual").sum()

col1.metric("Total Saham", total_saham)
col2.metric("🟢 Beli", jumlah_beli)
col3.metric("⚖️ Tahan", jumlah_tahan)
col4.metric("🔴 Jual", jumlah_jual)

# =========================
# Ranking
# =========================
st.subheader("🏆 Ranking Saham Terbaik")

top_df = df[[
    "Ticker", "Harga", "PER", "PBV", "ROE (%)",
    "Fair Value", "Upside (%)", "Rekomendasi", "Score"
]].copy()

styled_top_df = (
    top_df.style
    .format({
        "Harga": lambda x: format_number(x, 2),
        "PER": lambda x: format_number(x, 2),
        "PBV": lambda x: format_number(x, 2),
        "ROE (%)": lambda x: format_number(x, 2),
        "Fair Value": lambda x: format_number(x, 2),
        "Upside (%)": lambda x: format_number(x, 2),
        "Score": lambda x: format_number(x, 0),
    })
    .map(style_recommendation, subset=["Rekomendasi"])
)

st.dataframe(styled_top_df, use_container_width=True)

# =========================
# Tabel utama
# =========================
st.subheader("📋 Ringkasan Fundamental")

main_df = df[[
    "Ticker", "Harga", "EPS", "PER", "PBV", "ROE (%)",
    "Fair Value", "Upside (%)", "Undervalued", "Rekomendasi", "Score"
]].copy()

styled_main_df = (
    main_df.style
    .format({
        "Harga": lambda x: format_number(x, 2),
        "EPS": lambda x: format_number(x, 2),
        "PER": lambda x: format_number(x, 2),
        "PBV": lambda x: format_number(x, 2),
        "ROE (%)": lambda x: format_number(x, 2),
        "Fair Value": lambda x: format_number(x, 2),
        "Upside (%)": lambda x: format_number(x, 2),
        "Score": lambda x: format_number(x, 0),
    })
    .map(style_recommendation, subset=["Rekomendasi"])
)

st.dataframe(styled_main_df, use_container_width=True)

# =========================
# Chart perbandingan
# =========================
if show_comparison_chart and histories:
    st.subheader("📉 Perbandingan Performa Harga (Base 100)")
    all_hist = pd.concat(histories, ignore_index=True)

    visible_tickers = df["Ticker"].tolist()
    all_hist = all_hist[all_hist["Ticker"].isin(visible_tickers)]

    if not all_hist.empty:
        comparison_chart = (
            alt.Chart(all_hist)
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Tanggal"),
                y=alt.Y("Indexed:Q", title="Indexed Performance (Base 100)"),
                color="Ticker:N",
                tooltip=["Date:T", "Ticker:N", alt.Tooltip("Indexed:Q", format=".2f")]
            )
            .properties(height=420)
            .interactive()
        )
        st.altair_chart(comparison_chart, use_container_width=True)

# =========================
# Chart historis per saham
# =========================
if show_charts:
    st.subheader("📊 Harga Historis per Saham")
    for ticker in df["Ticker"].tolist():
        summary = get_summary_data(ticker)
        if summary and not summary["hist"].empty:
            hist_df = summary["hist"].reset_index()[["Date", "Close"]]

            chart = (
                alt.Chart(hist_df)
                .mark_line()
                .encode(
                    x=alt.X("Date:T", title="Tanggal"),
                    y=alt.Y("Close:Q", title="Harga Penutupan"),
                    tooltip=["Date:T", alt.Tooltip("Close:Q", format=".2f")]
                )
                .properties(height=280, title=ticker)
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)

# =========================
# Catatan
# =========================
st.markdown("---")
st.caption(
    "Metode fair value di dashboard ini masih sederhana: Fair Value = EPS × 15. "
    "Gunakan sebagai screening awal, bukan satu-satunya dasar keputusan investasi."
)
# Build Dataset
# =========================
rows = []
histories = []

for ticker in tickers:
    data = get_stock_data(ticker)
    if not data:
        continue

    recommendation = classify_recommendation(data)
    score = calculate_score(data, screen_mode)

    row = {
        "Ticker": data["ticker"],
        "Name": data["name"],
        "Sector": data["sector"],
        "Industry": data["industry"],
        "Price": data["price"],
        "EPS": data["eps"],
        "PER": data["per"],
        "PBV": data["pbv"],
        "ROE (%)": data["roe"],
        "Dividend Yield (%)": data["dividend_yield"],
        "Fair Value": data["fair_value"],
        "Upside (%)": data["upside_pct"],
        "Undervalued": data["undervalued"],
        "Recommendation": recommendation,
        "Score": score,
        "Market Cap": data["market_cap"],
    }
    rows.append(row)

    hist = data["hist"].copy().reset_index()
    if not hist.empty:
        base = hist["Close"].iloc[0]
        if pd.notna(base) and base != 0:
            hist["Indexed"] = (hist["Close"] / base) * 100
            hist["Ticker"] = ticker
            histories.append(hist[["Date", "Ticker", "Close", "Indexed"]])

df = pd.DataFrame(rows)

st.title("📈 Professional Stock Screener")
st.caption(
    f"Updated from Yahoo Finance | Screening: {screening_badge(screen_mode)} | "
    f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

if df.empty:
    st.info("Belum ada data yang berhasil diambil.")
    st.stop()

# =========================
# Filters
# =========================
filtered = df.copy()

filtered = filtered[
    ((filtered["ROE (%)"].isna()) | (filtered["ROE (%)"] >= min_roe)) &
    ((filtered["PER"].isna()) | (filtered["PER"] <= max_per)) &
    ((filtered["PBV"].isna()) | (filtered["PBV"] <= max_pbv))
]

if screen_mode == "Dividend + Value":
    filtered = filtered[
        (filtered["Dividend Yield (%)"].isna()) | (filtered["Dividend Yield (%)"] >= min_div_yield)
    ]

if show_only_undervalued:
    filtered = filtered[filtered["Undervalued"] == True]

filtered = filtered.sort_values(
    by=["Score", "Upside (%)"],
    ascending=[False, False],
    na_position="last"
).reset_index(drop=True)

# =========================
# Top Metrics
# =========================
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Stocks", len(filtered))
col2.metric("BUY", int((filtered["Recommendation"] == "BUY").sum()))
col3.metric("HOLD", int((filtered["Recommendation"] == "HOLD").sum()))
col4.metric("SELL", int((filtered["Recommendation"] == "SELL").sum()))
avg_upside = filtered["Upside (%)"].dropna().mean() if not filtered["Upside (%)"].dropna().empty else None
col5.metric("Avg Upside", fmt_pct(avg_upside))

# =========================
# Download
# =========================
download_df = filtered.copy()
download_df["Undervalued"] = download_df["Undervalued"].map(lambda x: "Yes" if x else "No")
download_df["Recommendation"] = download_df["Recommendation"].map(recommendation_badge)

csv_data = download_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download CSV",
    data=csv_data,
    file_name="professional_stock_screener.csv",
    mime="text/csv"
)

# =========================
# Tabs
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Ranking", "Charts", "Detail"])

# =========================
# Tab 1: Overview
# =========================
with tab1:
    st.subheader("Overview Table")

    overview = filtered.copy()
    overview["Recommendation"] = overview["Recommendation"].map(recommendation_badge)
    overview["Undervalued"] = overview["Undervalued"].map(lambda x: "✅" if x else "❌")

    show_cols = [
        "Ticker", "Name", "Price", "PER", "PBV", "ROE (%)",
        "Dividend Yield (%)", "Fair Value", "Upside (%)",
        "Undervalued", "Recommendation", "Score"
    ]

    display_overview = overview[show_cols].copy()

    display_overview["Price"] = display_overview["Price"].apply(lambda x: fmt_num(x, 2))
    display_overview["PER"] = display_overview["PER"].apply(lambda x: fmt_num(x, 2))
    display_overview["PBV"] = display_overview["PBV"].apply(lambda x: fmt_num(x, 2))
    display_overview["ROE (%)"] = display_overview["ROE (%)"].apply(lambda x: fmt_pct(x, 2))
    display_overview["Dividend Yield (%)"] = display_overview["Dividend Yield (%)"].apply(lambda x: fmt_pct(x, 2))
    display_overview["Fair Value"] = display_overview["Fair Value"].apply(lambda x: fmt_num(x, 2))
    display_overview["Upside (%)"] = display_overview["Upside (%)"].apply(lambda x: fmt_pct(x, 2))
    display_overview["Score"] = display_overview["Score"].apply(lambda x: fmt_num(x, 0))

    st.dataframe(display_overview, use_container_width=True)

# =========================
# Tab 2: Ranking
# =========================
with tab2:
    st.subheader("Top Ranked Stocks")

    top_n = st.slider("Tampilkan Top N", 3, min(20, max(len(filtered), 3)), min(10, len(filtered)))
    ranking_df = filtered.head(top_n).copy()

    st.dataframe(
        ranking_df[[
            "Ticker", "Name", "Score", "Recommendation", "Upside (%)",
            "PER", "PBV", "ROE (%)", "Dividend Yield (%)"
        ]].assign(
            **{
                "Recommendation": lambda x: x["Recommendation"].map(recommendation_badge),
                "Upside (%)": lambda x: x["Upside (%)"].map(lambda v: fmt_pct(v, 2)),
                "PER": lambda x: x["PER"].map(lambda v: fmt_num(v, 2)),
                "PBV": lambda x: x["PBV"].map(lambda v: fmt_num(v, 2)),
                "ROE (%)": lambda x: x["ROE (%)"].map(lambda v: fmt_pct(v, 2)),
                "Dividend Yield (%)": lambda x: x["Dividend Yield (%)"].map(lambda v: fmt_pct(v, 2)),
                "Score": lambda x: x["Score"].map(lambda v: fmt_num(v, 0)),
            }
        ),
        use_container_width=True
    )

    if not ranking_df.empty:
        rank_chart = (
            alt.Chart(ranking_df)
            .mark_bar()
            .encode(
                x=alt.X("Score:Q", title="Score"),
                y=alt.Y("Ticker:N", sort="-x", title="Ticker"),
                tooltip=[
                    "Ticker", "Name",
                    alt.Tooltip("Score:Q", format=".0f"),
                    alt.Tooltip("Upside (%):Q", format=".2f"),
                    alt.Tooltip("ROE (%):Q", format=".2f"),
                    alt.Tooltip("Dividend Yield (%):Q", format=".2f"),
                ]
            )
            .properties(height=420)
        )
        st.altair_chart(rank_chart, use_container_width=True)

# =========================
# Tab 3: Charts
# =========================
with tab3:
    st.subheader("Performance Comparison")

    visible_tickers = filtered["Ticker"].tolist()
    if histories and visible_tickers:
        all_hist = pd.concat(histories, ignore_index=True)
        all_hist = all_hist[all_hist["Ticker"].isin(visible_tickers)]

        if not all_hist.empty:
            chart_compare = (
                alt.Chart(all_hist)
                .mark_line()
                .encode(
                    x=alt.X("Date:T", title="Date"),
                    y=alt.Y("Indexed:Q", title="Indexed Performance (Base 100)"),
                    color=alt.Color("Ticker:N"),
                    tooltip=[
                        "Ticker:N",
                        "Date:T",
                        alt.Tooltip("Indexed:Q", format=".2f"),
                        alt.Tooltip("Close:Q", format=".2f"),
                    ]
                )
                .properties(height=450)
                .interactive()
            )
            st.altair_chart(chart_compare, use_container_width=True)
        else:
            st.info("Belum ada data historis untuk comparison chart.")
    else:
        st.info("Belum ada data historis untuk comparison chart.")

    st.subheader("Valuation Scatter")

    scatter_source = filtered.dropna(subset=["PER", "ROE (%)"]).copy()
    if not scatter_source.empty:
        scatter = (
            alt.Chart(scatter_source)
            .mark_circle(size=140)
            .encode(
                x=alt.X("PER:Q", title="PER"),
                y=alt.Y("ROE (%):Q", title="ROE (%)"),
                size=alt.Size("Upside (%):Q", title="Upside (%)"),
                color=alt.Color("Recommendation:N"),
                tooltip=[
                    "Ticker", "Name",
                    alt.Tooltip("PER:Q", format=".2f"),
                    alt.Tooltip("PBV:Q", format=".2f"),
                    alt.Tooltip("ROE (%):Q", format=".2f"),
                    alt.Tooltip("Upside (%):Q", format=".2f"),
                    alt.Tooltip("Dividend Yield (%):Q", format=".2f"),
                ]
            )
            .properties(height=450)
            .interactive()
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("Data PER/ROE belum cukup untuk scatter chart.")

# =========================
# Tab 4: Detail
# =========================
with tab4:
    st.subheader("Stock Detail")

    detail_options = filtered["Ticker"].tolist()
    if detail_options:
        selected_detail = st.selectbox("Pilih saham", detail_options)
        detail_row = filtered[filtered["Ticker"] == selected_detail].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", fmt_num(detail_row["Price"], 2))
        c2.metric("Fair Value", fmt_num(detail_row["Fair Value"], 2))
        c3.metric("Upside", fmt_pct(detail_row["Upside (%)"], 2))
        c4.metric("Recommendation", recommendation_badge(detail_row["Recommendation"]))

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("PER", fmt_num(detail_row["PER"], 2))
        c6.metric("PBV", fmt_num(detail_row["PBV"], 2))
        c7.metric("ROE", fmt_pct(detail_row["ROE (%)"], 2))
        c8.metric("Dividend Yield", fmt_pct(detail_row["Dividend Yield (%)"], 2))

        st.markdown("### Company Profile")
        st.write(f"**Name:** {detail_row['Name']}")
        st.write(f"**Sector:** {detail_row['Sector'] or '-'}")
        st.write(f"**Industry:** {detail_row['Industry'] or '-'}")
        st.write(f"**Market Cap:** {fmt_num(detail_row['Market Cap'], 0)}")
        st.write(f"**Undervalued:** {'Yes' if detail_row['Undervalued'] else 'No'}")
        st.write(f"**Score:** {fmt_num(detail_row['Score'], 0)}")

        selected_hist = None
        for h in histories:
            if not h.empty and h["Ticker"].iloc[0] == selected_detail:
                selected_hist = h.copy()
                break

        if selected_hist is not None and not selected_hist.empty:
            st.markdown("### Historical Price")
            detail_chart = (
                alt.Chart(selected_hist)
                .mark_line()
                .encode(
                    x=alt.X("Date:T", title="Date"),
                    y=alt.Y("Close:Q", title="Close Price"),
                    tooltip=[
                        "Date:T",
                        alt.Tooltip("Close:Q", format=".2f")
                    ]
                )
                .properties(height=400)
                .interactive()
            )
            st.altair_chart(detail_chart, use_container_width=True)
    else:
        st.info("Tidak ada saham yang lolos filter.")

# =========================
# Footer
# =========================
st.markdown("---")
st.caption(
    "Catatan: fair value pada aplikasi ini masih memakai pendekatan sederhana: EPS × 15. "
    "Gunakan untuk screening awal, bukan sebagai satu-satunya dasar keputusan investasi."
)


