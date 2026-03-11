import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import pytz
from datetime import datetime, time as dt_time

# ============= [TELEGRAM CONFIG] =============
TOKEN = "8243045012:AAFJ3mP82vM4ra_EneL_vup7-wA6qGOYsN8"
CHAT_ID = "937617402"

if 'sent_alerts' not in st.session_state:
    st.session_state.sent_alerts = set()

def send_telegram_msg(message, alert_key):
    if alert_key not in st.session_state.sent_alerts:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=HTML&disable_web_page_preview=true"
            requests.get(url, timeout=5)
            st.session_state.sent_alerts.add(alert_key)
        except: pass

# ============= [1] UI & PROFESSIONAL CSS (STRICT HIDE ENABLED) =============
st.set_page_config(page_title="HEYFUND", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #2E2D2D; color: #e0e0e0; opacity: 1 !important; visibility: visible !important; }
    div[data-testid="stStatusWidget"], [data-testid="stStatusWidget"], .stStatusWidget,
    div[class*="stStatusWidget"], div[data-testid="stSpinner"],
    header[data-testid="stHeader"] .st-emotion-cache-p5m613, .st-emotion-cache-p5m613 {
        display: none !important; visibility: hidden !important; height: 0px !important;
    }
    @keyframes golden-glow {
        0% { background-color: #0e161f; box-shadow: none; }
        50% { background-color: #b8860b; box-shadow: 0 0 15px #ffd700; }
        100% { background-color: #0e161f; box-shadow: none; }
    }
    .pdh-alert { animation: golden-glow 1.5s ease-in-out; animation-iteration-count: 40; border: 1.5px solid #ffd700 !important; }
    .market-status-bar { display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding: 5px; font-family: monospace; }
    .status-dot { height: 8px; width: 8px; border-radius: 50%; animation: dot-blink 1.5s infinite; }
    @keyframes dot-blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .dot-green { background-color: #00c853; box-shadow: 0 0 8px #00c853; }
    .dot-red { background-color: #ff5252; }
    .status-badge { border: 1px solid #00c853; color: #00c853; padding: 1px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }
    .status-badge-closed { border: 1px solid #ff5252; color: #ff5252; padding: 1px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }
    .market-time { color: #ffd700; font-size: 18px; font-weight: bold; }
    .tag-container { display: inline-flex; gap: 2px; vertical-align: middle; margin-left: 4px; }
    .tag-box { font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px; display: inline-block; }
    .tag-wb { background: #ffd700; color: #000; }
    .tag-pdh { background: #00c853; color: #000; }
    .tag-pdl { background: #ff5252; color: #fff; }
    .vol-text-green { color: #00FF2F !important; font-weight: bold; }
    .rsi-text-yellow { color: #ffd700 !important; font-weight: bold; }
    .price-container { font-size: 15px; font-weight: bold; margin-top: 4px; }
    .change-text { font-size: 11px; margin-left: 5px; opacity: 0.9; }
    .idx-card { background: #0e161f; border: 1px solid #1c2a38; border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
    .idx-price { font-size: 18px; font-weight: bold; color: white; }
    .grid-box { background-color: #0e161f; border: 1px solid #1c2a38; border-radius: 4px; padding: 10px; height: 140px; border-left: 3px solid #1c2a38; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
    .leader-header { background: #1c2a38; padding: 8px; border-radius: 6px; font-size: 13px; font-weight: bold; color: #ffd700; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .count-badge { background: #ffd700; color: #000; padding: 1px 6px; border-radius: 10px; font-size: 11px; }
    .scanner-row { background-color: #0e161f; padding: 12px; border-bottom: 1px solid #151f2b; display: flex; justify-content: space-between; align-items: flex-start; }
    a { text-decoration: none !important; color: inherit; }
    div[data-testid="stTextInput"] { width: 180px !important; margin-left: auto; }
    </style>
    """, unsafe_allow_html=True)

# ============= [2] DATA ENGINE =============
def get_supertrend_list(df, period=9, multiplier=2):
    if len(df) < period: return [True] * len(df)
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([high-low, abs(high-close.shift(1)), abs(low-close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2
    f_up = hl2 + (multiplier * atr); f_lo = hl2 - (multiplier * atr)
    st_list = [True] * len(df)
    for i in range(1, len(df)):
        if close.iloc[i] > f_up.iloc[i-1]: st_list[i] = True
        elif close.iloc[i] < f_lo.iloc[i-1]: st_list[i] = False
        else: st_list[i] = st_list[i-1]
    return st_list

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=60)
def get_advanced_market_data():
    idx_symbols = {'^NSEI' : 'NIFTY 50', '^BSESN': 'SENSEX', '^NSEBANK': 'NIFTY BANK', 'NIFTY_FIN_SERVICE.NS': 'FIN NIFTY'}
    stocks = ['COALINDIA', 'DMART', 'MCX', 'NATIONALUM', 'RELIANCE', 'ONGC', 'WIPRO', 'PERSISTENT', 'SUNPHARMA', 'TORNTPHARM', 'PAGEIND', 'HCLTECH', 'OFSS', 'LTIM', 'NTPC', 'TECHM', 'DRREDDY', 'OIL', 'ALKEM', 'INFY', 'CIPLA', 'MARICO', 'ICICIGI', 'SOLARINDS', 'HINDALCO', 'TCS', 'VEDL', 'BSE', 'ITC', 'MPHASIS', 'HEROMOTOCO', 'TATAELXSI', 'SBILIFE', 'APOLLOHOSP', 'BHARTIARTL', 'PHOENIXLTD', 'DIVISLAB', 'TATAPOWER', 'AUROPHARMA', 'HAL', 'VBL', 'MANKIND', 'SWIGGY', 'ABB', 'LUPIN', 'JUBLFOOD', 'NESTLEIND', 'BIOCON', 'PPLPHARMA', 'PIIND', 'MAXHEALTH', 'COFORGE', 'ZYDUSLIFE', 'BRITANNIA', 'OBEROIRLTY', 'HINDUNILVR', 'KFINTECH', 'MFSL', 'CAMS', 'SYNGENE', 'TATATECH', 'SRF', 'UNITDSPR', 'COLPAL', 'SUPREMEIND', 'GODREJPROP', 'BAJAJHLDNG', 'TITAN', 'JINDALSTEL', 'NAUKRI', 'GRASIM', 'HDFCLIFE', 'TATACONSUM', 'KALYANKJIL', 'POWERGRID', 'IEX', 'HINDZINC', 'UPL', 'HAVELLS', 'GLENMARK', 'DABUR', 'ADANIENSOL', 'IRCTC', 'ADANIGREEN', 'CUMMINSIND', 'KOTAKBANK', 'DIXON', 'KPITTECH', 'PETRONET', 'WAAREEENER', '360ONE', 'ICICIPRULI', 'PATANJALI', 'SAMMAANCAP', 'PREMIERENE', 'POWERINDIA', 'CDSL', 'DLF', 'LODHA', 'NYKAA', 'BOSCHLTD', 'BHEL', 'POLICYBZR', 'CONCOR', 'HDFCBANK', 'BLUESTARCO', 'PRESTIGE', 'SHREECEM', 'CROMPTON', 'MUTHOOTFIN', 'DALBHARAT', 'ASTRAL', 'LICI', 'FORTIS', 'BAJAJ-AUTO', 'BAJAJFINSV', 'VOLTAS', 'HDFCAMC', 'TRENT', 'SONACOMS', 'BDL', 'AUBANK', 'BEL', 'EXIDEIND', 'LAURUSLABS', 'AMBER', 'INDUSTOWER', 'IREDA', 'ABCAPITAL', 'KEI', 'BAJFINANCE', 'M&M', 'INDHOTEL', 'KAYNES', 'SIEMENS', 'TORNTPOWER', 'NUVAMA', 'POLYCAB', 'ICICIBANK', 'RVNL', 'AXISBANK', 'TIINDIA', 'JSWSTEEL', 'LICHSGFIN', 'CGPOWER', 'ANGELONE', 'TVSMOTOR', 'INDUSINDBK', 'GODREJCP', 'RBLBANK', 'APLAPOLLO', 'ULTRACEMCO', 'ADANIPORTS', 'SBICARD', 'JSWENERGY', 'EICHERMOT', 'LTF', 'PIDILITIND', 'BANKBARODA', 'DELHIVERY', 'AMBUJACEM', 'MANAPPURAM', 'ADANIENT', 'BHARATFORG', 'RECLTD', 'GAIL', 'ASIANPAINT', 'PNBHOUSING', 'MARUTI', 'PFC', 'PAYTM', 'TATASTEEL', 'HUDCO', 'JIOFIN', 'FEDERALBNK', 'MAZDOCK', 'CHOLAFIN', 'INDIANB', 'LT', 'ASHOKLEY', 'BANDHANBNK', 'SAIL', 'SHRIRAMFIN', 'CANBK', 'PNB', 'UNOMINDA', 'SBIN', 'IOC', 'BANKINDIA', 'MOTHERSON', 'UNIONBANK', 'BPCL', 'HINDPETRO', 'INDIGO']
    
    unique_tickers = list(set([s + ".NS" for s in stocks] + list(idx_symbols.keys())))
    try:
        data = yf.download(unique_tickers, period="150d", interval="1d", group_by='ticker', threads=True, progress=False)
        idx_res = []
        for sym, name in idx_symbols.items():
            t_data = data[sym].dropna(); cp, pcp = t_data['Close'].iloc[-1], t_data['Close'].iloc[-2]
            idx_res.append({'name': name, 'val': f"{cp:,.2f}", 'pts': round(cp-pcp, 2), 'pct': round(((cp-pcp)/pcp)*100, 2)})

        stock_res = []
        tz_ind = pytz.timezone('Asia/Kolkata'); current_date = datetime.now(tz_ind).strftime("%Y%m%d")
        for s in stocks:
            try:
                t = s + ".NS"; t_df = data[t].dropna(); cp, pcp = t_df['Close'].iloc[-1], t_df['Close'].iloc[-2]
                hi, lo = t_df['High'].iloc[-2], t_df['Low'].iloc[-2]; w_high = t_df['High'].iloc[-6:-1].max()
                v_ratio = round(t_df['Volume'].iloc[-1] / (t_df['Volume'].iloc[-6:-1].mean() + 1e-9), 2)
                rsi_val = round(calculate_rsi(t_df['Close']).iloc[-1], 1)
                w_trends = get_supertrend_list(t_df.resample('W').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna(), 9, 2)
                
                # Alerts
                alert_key = f"{s}_{current_date}"
                if w_trends[-1] and not w_trends[-2]: send_telegram_msg(f"🏆 <b> BUY</b>: {s} @ ₹{round(cp,2)} 🟢", alert_key+"buy")
                if cp > hi and cp > w_high and v_ratio >= 2.0: send_telegram_msg(f"🚀 <b>BREAKOUT</b>: {s} @ ₹{round(cp,2)} 🟢", alert_key+"break")

                tag_type = 'PDH' if cp > hi else ('PDL' if cp < lo else 'ZONE')
                tags_html = f'<div class="tag-container">' + (f'<span class="tag-box tag-pdh">PDH</span>' if cp > hi else (f'<span class="tag-box tag-pdl">PDL</span>' if cp < lo else '<span class="tag-box tag-zone">ZONE</span>')) + (f'<span class="tag-box tag-wb">WB</span>' if cp > w_high else '') + '</div>'
                stock_res.append({'Stock': s, 'LTP': round(cp, 2), 'Pts': round(cp-pcp, 2), 'Pct': round(((cp-pcp)/pcp)*100, 2), 'VolRatio': v_ratio, 'RSI': rsi_val, 'TagClass': tag_type, 'FullTags': tags_html, 'Logo': f"https://s3-symbol-logo.tradingview.com/{s.lower()}--big.svg", 'Buy': w_trends[-1] and not w_trends[-2], 'Sell': not w_trends[-1] and w_trends[-2], 'WeeklyGreen': w_trends[-1]})
            except: continue
        return idx_res, pd.DataFrame(stock_res)
    except: return [], pd.DataFrame()

# ============= [3] UI STRUCTURE =============
h1, h2 = st.columns([3, 1])
with h1: st.title("🛡️ HEYFUND")
with h2:
    @st.fragment(run_every=1)
    def show_clock_live():
        tz = pytz.timezone('Asia/Kolkata'); now = datetime.now(tz)
        is_open = now.weekday() < 5 and (dt_time(9,15) <= now.time() <= dt_time(15,30))
        st.markdown(f'<div class="market-status-bar"><div class="status-dot {"dot-green" if is_open else "dot-red"}"></div><div class="{"status-badge" if is_open else "status-badge-closed"}">{"LIVE" if is_open else "CLOSED"}</div><div class="market-time">{now.strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)
    show_clock_live()

@st.fragment(run_every=60)
def show_dashboard_silent():
    try: requests.get("https://google.com", timeout=1)
    except: pass
    indices, df = get_advanced_market_data()
    if indices:
        idx_cols = st.columns(4)
        for i, idx in enumerate(indices):
            color = "#00c853" if idx['pts'] >= 0 else "#ff5252"; arrow = "↑" if idx['pts'] >= 0 else "↓"
            with idx_cols[i]:
                st.markdown(f"""<div class="idx-card"><div><div style="font-size:11px; font-weight:bold;">{idx['name']}</div><div class="idx-price" style="font-size:20px;"><span style="color:{color};">{arrow}</span> {idx['val']}</div></div><div style="text-align:right; color:{color}; font-weight:bold;"><div>{idx['pct']}%</div><div>{idx['pts']}</div></div></div>""", unsafe_allow_html=True)

    tab_lead, tab_all, tab_intra, tab_scan = st.tabs(["🏆 LEADERS", "📋 ALL STOCKS", "⚡ INTRADAY", "🔍 SCANNER"])

    def draw_grid_boxes(data):
        if data.empty: st.info("No stocks matching this category.")
        else:
            g_cols = st.columns(7)
            for i, (idx, row) in enumerate(data.iterrows()):
                color = "#00c853" if row['Pts'] > 0 else "#ff5252"; v_c = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                with g_cols[i % 7]:
                    st.markdown(f"""
                        <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                            <div class="grid-box {"pdh-alert" if row["TagClass"]=="PDH" else ""}" style="border-left:3px solid {color}; margin-bottom:10px;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;"><span style="font-size:11px; font-weight:bold; color:#8a99a8;">{row['Stock']}</span>{row['FullTags']}</div>
                                <div class="price-container" style="color:{color};">₹{row['LTP']}</div>
                                <div style="font-size:11px; color:{color}; margin-top:-5px;">{'+' if row['Pts']>0 else ''}{row['Pts']} ({row['Pct']}%)</div>
                                <div style="display:flex; justify-content:space-between; border-top:1px solid #1c2a38; padding-top:4px; font-size:10px;">
                                    <span class="{v_c}">x{row['VolRatio']} V</span><span class="rsi-text-yellow">RSI:{row['RSI']}</span>
                                </div>
                            </div>
                        </a>""", unsafe_allow_html=True)

    with tab_all:
        s_term = st.text_input("🔍 Search Symbols...", value="", key="search_bar").upper()
        draw_grid_boxes(df[df['Stock'].str.contains(s_term)] if s_term else df)

    with tab_lead:
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            def draw_leader_list(title, d, col):
                with col:
                    st.markdown(f'<div class="leader-header"><span>{title}</span><span class="count-badge">{len(d.head(10))}</span></div>', unsafe_allow_html=True)
                    for _, row in d.head(10).iterrows():
                        color = "#00c853" if row['Pts'] > 0 else "#ff5252"; v_c = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                        st.markdown(f"""
                        <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                            <div class="scanner-row {"pdh-alert" if row["TagClass"]=="PDH" else ""}">
                                <div style="display:flex; gap:10px; align-items:center;">
                                    <img src="{row['Logo']}" style="width:20px; border-radius:50%;">
                                    <div><b style="color:white; font-size:13px;">{row['Stock']}</b>{row['FullTags']}<br>
                                    <span style="color:{color}; font-size:12px;">₹{row['LTP']} ({row['Pct']}%)</span></div>
                                </div>
                                <div style="text-align:right;" class="{v_c}">x{row['VolRatio']} Vol</div>
                            </div>
                        </a>""", unsafe_allow_html=True)
            draw_leader_list("GAINERS", df[df['Pts'] > 0].sort_values('Pct', ascending=False), c1)
            draw_leader_list("LOSERS", df[df['Pts'] < 0].sort_values('Pct', ascending=True), c2)
            draw_leader_list("VOL SHOCKERS", df.sort_values(by=['Pts', 'VolRatio'], ascending=[False, False]), c3)

    with tab_intra:
        b, r, n = df[df['TagClass']=='PDH'], df[df['TagClass']=='PDL'], df[df['TagClass']=='ZONE']
        st_b, st_r, st_n = st.tabs([f"🟢 BULLISH ({len(b)})", f"🔴 BEARISH ({len(r)})", f"⚪ NEUTRAL ({len(n)})"])
        with st_b: draw_grid_boxes(b)
        with st_r: draw_grid_boxes(r)
        with st_n: draw_grid_boxes(n)

    with tab_scan:
        if not df.empty:
            s1, s2, s3, s4 = st.columns(4)
            def draw_scanner_col(title, d, col):
                with col:
                    st.markdown(f'<div class="leader-header"><span>{title}</span><span class="count-badge">{len(d.head(10))}</span></div>', unsafe_allow_html=True)
                    for _, row in d.head(10).iterrows():
                        color = "#00c853" if row['Pts'] > 0 else "#ff5252"; v_c = "vol-text-green" if row['VolRatio'] >= 1.8 else ""
                        st.markdown(f"""
                        <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                            <div class="scanner-row {"pdh-alert" if row["TagClass"]=="PDH" else ""}">
                                <div style="display:flex; gap:10px; align-items:center;">
                                    <img src="{row['Logo']}" style="width:20px; border-radius:50%;">
                                    <div><b style="color:white; font-size:13px;">{row['Stock']}</b>{row['FullTags']}<br>
                                    <span style="color:{color}; font-size:12px;">₹{row['LTP']} ({row['Pct']}%)</span></div>
                                </div>
                                <div style="text-align:right;" class="{v_c}">x{row['VolRatio']} Vol</div>
                            </div>
                        </a>""", unsafe_allow_html=True)
            draw_scanner_col("🏆 BUY", df[df['Buy']], s1)
            draw_scanner_col("🩸 SELL", df[df['Sell']], s2)
            draw_scanner_col("💪 STRONG BUY", df[(df['WeeklyGreen']) & (df['RSI'] > 60)], s3)
            draw_scanner_col("🚀 BREAKOUT", df[df['VolRatio'] >= 1.8], s4)

show_dashboard_silent()
