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
python --version
python -m venv .venv
.venv\Scripts\activate   # Windows
python -m pip install --upgrade pip --default-timeout=600 --no-cache-dir -i https://pypi.org/simple
pip install -r requirements.txt
streamlit run app/streamlit_app.py
