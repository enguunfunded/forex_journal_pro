import pandas as pd
import yfinance as yf
from datetime import timedelta

def get_ohlcv_window(symbol, entry_time, minutes_before=90, minutes_after=30):
    ticker = {"XAUUSD":"GC=F","EURUSD":"EURUSD=X"}.get(symbol,symbol)
    df = yf.download(ticker, period="2d", interval="1m", progress=False).reset_index()
    df = df.rename(columns={"Datetime":"Datetime"})
    start = entry_time - timedelta(minutes=minutes_before)
    end = entry_time + timedelta(minutes=minutes_after)
    return df[(df["Datetime"]>=start)&(df["Datetime"]<=end)]
