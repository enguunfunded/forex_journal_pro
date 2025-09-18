import streamlit as st
from datetime import datetime
import os
import pandas as pd
from components.db import init_db, get_session, get_engine, Trade, ChecklistItem, TradeChecklist
from components.utils import infer_session, mtf_alignment_score
from components.plotting import save_candles_image
from components.data_fetch import get_ohlcv_window
from sqlalchemy.orm import Session
from sqlalchemy import select, func

st.set_page_config(page_title="Forex Journal Pro", layout="wide")

DB_PATH = os.path.join(os.path.dirname(__file__), "journal.db")
init_db(DB_PATH)

st.title("📒 Forex Journal Pro")

tabs = st.tabs(["➕ New Entry","📊 Dashboard","📁 Data"])

# === New Trade Entry ===
with tabs[0]:
    st.subheader("New Trade Entry")
    with st.form("new_trade"):
        symbol = st.text_input("Symbol", "XAUUSD").upper().strip()
        direction = st.selectbox("Direction", ["BUY","SELL"])
        # Entry time (date + time → datetime)
        d = st.date_input("Entry date", value=datetime.now().date())
        t = st.time_input("Entry time", value=datetime.now().time().replace(microsecond=0))
        entry_time = datetime.combine(d, t)

        rr = st.number_input("Risk:Reward", value=3.0)
        result = st.selectbox("Result", ["OPEN","WIN","LOSS","BE"])
        notes = st.text_area("Notes")

        h4_dir = st.selectbox("H4 Direction", ["UP","DOWN","RANGE"])
        h1_dir = st.selectbox("H1 Direction", ["UP","DOWN","RANGE"])
        m15_dir = st.selectbox("M15 Direction", ["UP","DOWN","RANGE"])

        conds = {
    "asia_range_sweep": st.checkbox("Азийн мужийн liquidity sweep"),
    "bos_choch": st.checkbox("BOS/CHOCH (бүтцийн эвдрэл)"),
    "fvg_retracement": st.checkbox("FVG буцаалт"),
    "volume_spike": st.checkbox("Эзлэхүүн огцом өсөлт"),
    "order_block": st.checkbox("Order Block (захиалгын блок)"),
    "breaker_block": st.checkbox("Breaker Block"),
    "liquidity_grab": st.checkbox("Liquidity авах хөдөлгөөн"),
    "equal_highs_lows": st.checkbox("Тэгш high/low түвшин"),
    "daily_bias": st.checkbox("Өдрийн чиглэл давхцах"),
    "session_open": st.checkbox("Сешн нээлтийн нөлөө"),
    "news_event": st.checkbox("Мэдээний нөлөө"),
    "trendline_liquidity": st.checkbox("Trendline liquidity sweep"),
             # 1. Толгой мөрүүд
    "head_shoulders_4h": st.checkbox("Head & Shoulders (4H)"),
    "head_shoulders_1h": st.checkbox("Head & Shoulders (1H)"),
    "head_shoulders_15m": st.checkbox("Head & Shoulders (15M)"),

    # 2. GD
    "gd_cross": st.checkbox("Golden/Death Cross (GD)"),

    # 3. Trendline
    "trendline_confluence": st.checkbox("Trendline давхцал"),

    # 4. Key Levels
    "key_level_4h": st.checkbox("Key Level (4H)"),
    "key_level_1h": st.checkbox("Key Level (1H)"),
    "key_level_15m": st.checkbox("Key Level (15M)"),
}


        # ✅ Submit товч формын дотор байх ёстой
        submit = st.form_submit_button("Save")

    # ✅ Хадгалах логик
    if submit:
        session_name = infer_session(entry_time)
        mtf_score = mtf_alignment_score(h4_dir, h1_dir, m15_dir)
        with get_session(DB_PATH) as s:
            trade = Trade(
                symbol=symbol, direction=direction, entry_time=entry_time,
                rr=rr, result=result, h4_dir=h4_dir, h1_dir=h1_dir, m15_dir=m15_dir,
                mtf_score=mtf_score, session=session_name, notes=notes
            )
            s.add(trade); s.commit()
            trade_id = trade.id

            for key, checked in conds.items():
                if checked:
                    # аль хэдийн байгаа эсэхийг шалгах
                    item = s.execute(select(ChecklistItem).where(ChecklistItem.key == key)).scalar_one_or_none()
                    if item is None:
                        item = ChecklistItem(key=key, label=key.replace("_"," ").title())
                        s.add(item); s.flush()
                    s.add(TradeChecklist(trade_id=trade_id, item_id=item.id, checked=True))
            s.commit()
        st.success(f"Saved trade #{trade_id}")

# === Dashboard ===
with tabs[1]:
    st.subheader("Insights Dashboard")

    eng = get_engine()

    # Товч KPI-ууд
    with get_session(DB_PATH) as s:
        total  = s.scalar(select(func.count()).select_from(Trade)) or 0
        wins   = s.scalar(select(func.count()).where(Trade.result=="WIN")) or 0
        losses = s.scalar(select(func.count()).where(Trade.result=="LOSS")) or 0
        be     = s.scalar(select(func.count()).where(Trade.result=="BE"))   or 0
        open_  = s.scalar(select(func.count()).where(Trade.result=="OPEN")) or 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Wins", wins)
    c3.metric("Losses", losses)
    c4.metric("BE", be)
    c5.metric("Open", open_)

    st.markdown("### Winrate by Session")
    df = pd.read_sql_query("""
        SELECT session,
               SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END)*1.0 /
               NULLIF(SUM(CASE WHEN result IN ('WIN','LOSS','BE') THEN 1 ELSE 0 END),0) AS winrate,
               COUNT(*) AS trades
        FROM trade
        GROUP BY session
    """, eng)
    if not df.empty:
        st.dataframe(df.round(3), use_container_width=True)
    else:
        st.info("No data yet. Add trades to see session stats.")

    st.markdown("### Best Conditions (by session)")
    st.caption("Нөхцлийг ашигласан трейдийн winrate-ийг session-оор харуулна (≥3 трейд байх ёстой).")
    df2 = pd.read_sql_query("""
        SELECT t.session, ci.label,
               SUM(CASE WHEN t.result='WIN' THEN 1 ELSE 0 END)*1.0 / NULLIF(COUNT(*),0) AS winrate,
               COUNT(*) AS trades
        FROM trade_checklist tc
        JOIN checklist_item ci ON ci.id = tc.item_id
        JOIN trade t ON t.id = tc.trade_id
        GROUP BY t.session, ci.label
        HAVING COUNT(*) >= 3
        ORDER BY winrate DESC
    """, eng)
    if not df2.empty:
        st.dataframe(df2.round(3), use_container_width=True)
    else:
        st.info("Need ≥3 trades per condition to rank.")

# === Data ===
with tabs[2]:
    st.subheader("Data & Maintenance")

    eng = get_engine()

    # 1) Оролтуудын жагсаалт (+ checklist мэдээлэл)
    st.markdown("#### Trades (latest 100)")
    trades_df = pd.read_sql_query("""
        SELECT
            t.id,
            t.symbol,
            t.direction,
            t.session,
            t.rr,
            t.result,
            t.h4_dir,
            t.h1_dir,
            t.m15_dir,
            t.mtf_score,
            t.entry_time,
            t.notes,
            COUNT(tc.id) AS cond_count,                                   -- хэдэн нөхцөл идэвхтэй
            COALESCE(GROUP_CONCAT(ci.label, ' | '), '') AS conditions     -- ямар ямар нөхцөл
        FROM trade AS t
        LEFT JOIN trade_checklist AS tc ON tc.trade_id = t.id
        LEFT JOIN checklist_item  AS ci ON ci.id = tc.item_id
        GROUP BY t.id
        ORDER BY t.entry_time DESC
        LIMIT 100
    """, eng, parse_dates=["entry_time"])

    if trades_df.empty:
        st.info("No trades yet.")
    else:
        trades_df = trades_df.rename(columns={
            "cond_count": "conds",        # хэдэн checklist
            "entry_time": "time"          # илүү ойлгомжтой нэр
        })
        st.dataframe(trades_df, use_container_width=True)
            # --- View chart for a trade ---
    st.markdown("#### View chart of a trade")
    st.caption("Доорх 'View' товчийг дарж тухайн оролтын үедх OHLCV-г Entry/SL/Exit/TP шугамтайгаар харна.")

    import matplotlib.pyplot as plt

    def _plot_trade_chart(dfw, tr, show_tp=True):
        """Жижиг candlestick зураг зурах (mplfinance хэрэглэхгүй, matplotlib-оор гар аргаар)."""
        import numpy as np
        o = dfw["Open"].values
        h = dfw["High"].values
        l = dfw["Low"].values
        c = dfw["Close"].values
        x = np.arange(len(dfw))

        fig, ax = plt.subplots(figsize=(10, 4))
        # high-low шугам
        ax.vlines(x, l, h, linewidth=1)
        # body — өсөх/буурах
        up = c >= o
        down = ~up
        ax.bar(x[up], c[up] - o[up], bottom=o[up], width=0.6)
        ax.bar(x[down], o[down] - c[down], bottom=c[down], width=0.6)

        ax.set_title(f"{tr.symbol}  @ {tr.entry_time:%Y-%m-%d %H:%M}  ({tr.direction})")
        ax.set_xlabel("Bars")
        ax.set_ylabel("Price")

        # --- Entry/SL/Exit/TP шугамууд ---
        if tr.entry_price:
            ax.axhline(tr.entry_price, linestyle="--", linewidth=1.2, label=f"Entry {tr.entry_price:.2f}")
        if tr.sl_price:
            ax.axhline(tr.sl_price, linestyle=":", linewidth=1.2, label=f"SL {tr.sl_price:.2f}")
        if tr.exit_price:
            ax.axhline(tr.exit_price, linestyle="-.", linewidth=1.2, label=f"Exit {tr.exit_price:.2f}")

        # TP (RR шугам)
        if show_tp and tr.entry_price and tr.sl_price and tr.rr:
            risk = abs(tr.entry_price - tr.sl_price)
            if tr.direction.upper() == "BUY":
                tp = tr.entry_price + risk * tr.rr
            else:
                tp = tr.entry_price - risk * tr.rr
            ax.axhline(tp, linewidth=1.2, label=f"TP({tr.rr}R) {tp:.2f}")

        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.2)
        st.pyplot(fig, clear_figure=True)

    # Мөр бүрт "View" товч
    if not trades_df.empty:
        st.markdown("##### Recent trades (click View)")
        for _, row in trades_df.iterrows():
            c1, c2, c3 = st.columns([5, 3, 1])
            c1.write(f"#{int(row['id'])}  {row['symbol']}  {row['direction']}  {row['time']:%Y-%m-%d %H:%M}")
            c2.write(f"Result: {row['result']} | RR: {row['rr']}")
            if c3.button("View", key=f"view_{int(row['id'])}"):
with get_session(DB_PATH) as s:
    tr = s.get(Trade, int(row["id"]))

    try:
        # ✅ entry_time-ийг UTC aware болгоно (нөв бол)
        et = pd.Timestamp(tr.entry_time)
        if et.tzinfo is None:
            et = et.tz_localize("UTC")

        dfw = get_ohlcv_window(tr.symbol, et, minutes_before=90, minutes_after=60)

        # ✅ Хэрэв буцааж ирсэн дата UTC-тэй бол, график ашиглахаасаа өмнө timezone-оо авна
        if "Datetime" in dfw.columns:
            dt = pd.to_datetime(dfw["Datetime"])
            if dt.dt.tz is not None:
                dfw["Datetime"] = dt.dt.tz_convert(None)
        elif isinstance(dfw.index, pd.DatetimeIndex) and dfw.index.tz is not None:
            dfw.index = dfw.index.tz_convert(None)

        _plot_trade_chart(dfw, tr, show_tp=True)

    except Exception as e:
        st.error(f"Чарт ачаалахад алдаа: {e}")




    st.markdown("---")

    # 2) OHLCV CSV upload
    st.markdown("#### Upload OHLCV CSV (Datetime,Open,High,Low,Close,Volume)")
    up = st.file_uploader("CSV file", type=["csv"])
    if up:
        df_up = pd.read_csv(up)
        if "Datetime" in df_up.columns:
            df_up["Datetime"] = pd.to_datetime(df_up["Datetime"])
            df_up = df_up.sort_values("Datetime")
            sym = st.text_input("Symbol for this CSV", value="XAUUSD").upper()
            path = os.path.join(os.path.dirname(__file__), "data", f"{sym}.csv")
            df_up.to_csv(path, index=False)
            st.success(f"Saved CSV as {path}")
        else:
            st.error("CSV must include 'Datetime' column.")

    st.markdown("---")

    # 3) Бүх трейдийн лааны зургуудыг дахин үүсгэх
    st.markdown("#### Re-generate candlestick images")
    if st.button("Re-generate All Images"):
        with get_session(DB_PATH) as s:
            trades = s.query(Trade).all()
        ok = fail = 0
        for tr in trades:
            try:
                dfw = get_ohlcv_window(tr.symbol, tr.entry_time, minutes_before=90, minutes_after=30)
                save_candles_image(dfw, tr.symbol, tr.entry_time,
                    base_dir=os.path.join(os.path.dirname(__file__), "images"))
                ok += 1
            except Exception:
                fail += 1
        st.success(f"Done. OK={ok}, Fail={fail}")

    st.markdown("---")

    # 4) Checklist Manager – нөхцөл нэмэх/устгах
    st.markdown("#### Checklist Manager")
    new_label = st.text_input("New condition label", placeholder="Round number confluence")
    if st.button("Add condition") and new_label.strip():
        key = new_label.strip().lower().replace(" ", "_")
        with get_session(DB_PATH) as s:
            exists = s.execute(select(ChecklistItem).where(ChecklistItem.key==key)).scalar_one_or_none()
            if exists is None:
                s.add(ChecklistItem(key=key, label=new_label.strip()))
                s.commit()
                st.success(f"Added: {new_label}")
            else:
                st.warning("Already exists.")

    with get_session(DB_PATH) as s:
        items = s.execute(select(ChecklistItem)).scalars().all()
    if items:
        for it in items:
            c1, c2 = st.columns([4,1])
            c1.write(f"• {it.label}  (`{it.key}`)")
            if c2.button("Delete", key=f"del_{it.id}"):
                with get_session(DB_PATH) as s:
                    obj = s.get(ChecklistItem, it.id)
                    if obj:
                        s.delete(obj)
                        s.commit()
                        st.experimental_rerun()
    else:
        st.caption("No custom conditions yet.")
