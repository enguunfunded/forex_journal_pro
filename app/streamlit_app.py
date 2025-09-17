import streamlit as st
from datetime import datetime
import os
import pandas as pd
from components.db import init_db, get_session, Trade, ChecklistItem, TradeChecklist, get_engine
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
# === Dashboard ===
with tabs[1]:
    st.subheader("Insights Dashboard")

    eng = get_engine()

    # KPIs
    with get_session(DB_PATH) as s:
        total  = s.scalar(select(func.count()).select_from(Trade)) or 0
        wins   = s.scalar(select(func.count()).where(Trade.result == "WIN")) or 0
        losses = s.scalar(select(func.count()).where(Trade.result == "LOSS")) or 0
        be     = s.scalar(select(func.count()).where(Trade.result == "BE")) or 0
        open_  = s.scalar(select(func.count()).where(Trade.result == "OPEN")) or 0

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
    st.caption("Нөхцөлийг ашигласан трейдийн winrate-ийг session-оор (≥3 трейд) харуулна.")
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

    # 1) Trades list
    st.markdown("#### Trades (latest 100)")
    trades_df = pd.read_sql_query("""
        SELECT id, symbol, direction, session, rr, result,
               h4_dir, h1_dir, m15_dir, mtf_score, entry_time, notes
        FROM trade
        ORDER BY entry_time DESC
        LIMIT 100
    """, eng, parse_dates=["entry_time"])
    if trades_df.empty:
        st.info("No trades yet.")
    else:
        st.dataframe(trades_df, use_container_width=True)

    st.markdown("---")

    # 2) Upload OHLCV CSV
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

    # 3) Re-generate candlestick images
    st.markdown("#### Re-generate candlestick images")
    if st.button("Re-generate All Images"):
        with get_session(DB_PATH) as s:
            trades = s.query(Trade).all()
        ok = fail = 0
        for tr in trades:
            try:
                dfw = get_ohlcv_window(tr.symbol, tr.entry_time, minutes_before=90, minutes_after=30)
                save_candles_image(
                    dfw, tr.symbol, tr.entry_time,
                    base_dir=os.path.join(os.path.dirname(__file__), "images")
                )
                ok += 1
            except Exception:
                fail += 1
        st.success(f"Done. OK={ok}, Fail={fail}")

    st.markdown("---")

    # 4) Checklist Manager – add/delete
    st.markdown("#### Checklist Manager")
    new_label = st.text_input("New condition label", placeholder="Round number confluence")
    if st.button("Add condition") and new_label.strip():
        key = new_label.strip().lower().replace(" ", "_")
        with get_session(DB_PATH) as s:
            exists = s.execute(select(ChecklistItem).where(ChecklistItem.key == key)).scalar_one_or_none()
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

with tabs[0]:
    st.subheader("New Trade Entry")
    with st.form("new_trade"):
        symbol = st.text_input("Symbol", "XAUUSD").upper().strip()
        direction = st.selectbox("Direction", ["BUY","SELL"])
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
            "asia_range_sweep": st.checkbox("Asia range liquidity sweep"),
            "bos_choch": st.checkbox("BOS/CHOCH"),
            "fvg_retracement": st.checkbox("FVG retracement"),
            "volume_spike": st.checkbox("Volume spike"),
        }

        submit = st.form_submit_button("Save")

    if submit:
        session_name = infer_session(entry_time)
        mtf_score = mtf_alignment_score(h4_dir,h1_dir,m15_dir)
        with get_session(DB_PATH) as s:
            trade = Trade(
                symbol=symbol, direction=direction, entry_time=entry_time,
                rr=rr, result=result, h4_dir=h4_dir, h1_dir=h1_dir, m15_dir=m15_dir,
                mtf_score=mtf_score, session=session_name, notes=notes
            )
            s.add(trade)
            s.commit()
            trade_id = trade.id
            for key,checked in conds.items():
                if checked:
                    item = ChecklistItem(key=key,label=key)
                    s.add(item); s.commit()
                    s.add(TradeChecklist(trade_id=trade_id,item_id=item.id,checked=True))
            s.commit()
        st.success(f"Saved trade #{trade_id}")
