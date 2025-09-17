# Forex Journal Pro (Local)

A lightweight, local-first Forex trading journal with:
- Checklist-based entries
- Multi-timeframe direction checklist (H4, H1, M15)
- Session tagging (Asia / London / New York)
- Auto candlestick image capture
- Insights dashboard
- Runs locally with Streamlit + SQLite

## Quick Start
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app/streamlit_app.py
