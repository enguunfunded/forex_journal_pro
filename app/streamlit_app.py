import streamlit as st
from datetime import datetime
import os
import pandas as pd
from components.db import init_db, get_session, Trade, ChecklistItem, TradeChecklist
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
        entry_time = st.datetime_input("Entry Time", datetime.now())
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
