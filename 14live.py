import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import pytz # Added for IST
from datetime import datetime, time as dt_time

# ============= [TELEGRAM CONFIG] =============
TOKEN = "8243045012:AAFJ3mP82vM4ra_EneL_vup7-wA6qGOYsN8"
CHAT_ID = "937617402"


# ALERT MEMORY: Prevents duplicate alerts during tab switching
if 'sent_alerts' not in st.session_state:
    st.session_state.sent_alerts = set()

def send_telegram_msg(message, alert_key):
    # REFINED SPAM PROTECTION
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
    
    /* 🔴 STRICT HIDE & FOG FIX */
    div[data-testid="stStatusWidget"], [data-testid="stStatusWidget"], .stStatusWidget,
    div[class*="stStatusWidget"], div[data-testid="stSpinner"],
    header[data-testid="stHeader"] .st-emotion-cache-p5m613, .st-emotion-cache-p5m613 {
        display: none !important; visibility: hidden !important; height: 0px !important;
    }
    
    /* GOLDEN GLOW ANIMATION */
    @keyframes golden-glow {
        0% { background-color: #0e161f; box-shadow: none; }
        50% { background-color: #b8860b; box-shadow: 0 0 15px #ffd700; }
        100% { background-color: #0e161f; box-shadow: none; }
    }
    
    .pdh-alert { 
        animation: golden-glow 1.5s ease-in-out; 
        animation-iteration-count: 40; 
        border: 1.5px solid #ffd700 !important; 
    }

    /* 🟢 MARKET STATUS BAR */
    .market-status-bar {
        display: flex; align-items: center; justify-content: flex-end;
        gap: 10px; padding: 5px; font-family: monospace;
    }
    @keyframes dot-blink {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }
    .status-dot { height: 8px; width: 8px; border-radius: 50%; animation: dot-blink 1.5s infinite; }
    .dot-green { background-color: #00c853; box-shadow: 0 0 8px #00c853; }
    .dot-red { background-color: #ff5252; }
    
    .status-badge { border: 1px solid #00c853; color: #00c853; padding: 1px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }
    .status-badge-closed { border: 1px solid #ff5252; color: #ff5252; padding: 1px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }
    .market-time { color: #ffd700; font-size: 18px; font-weight: bold; }

    /* BOX TAGS STYLING */
    .tag-container { display: inline-flex; gap: 2px; vertical-align: middle; margin-left: 4px; }
    .tag-box { font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px; display: inline-block; }
    .tag-wb { background: #ffd700; color: #000; }
    .tag-pdh { background: #00c853; color: #000; }
    .tag-pdl { background: #ff5252; color: #fff; }
    .tag-news-pos { background: #00c853; color: #000; }
    .tag-news-neg { background: #ff5252; color: #fff; }

    /* 🟢 RE-ADDED VOLUME & RSI COLORS */
    .vol-text-green { color: #00FF2F !important; font-weight: bold; }
    .rsi-text-yellow { color: #ffd700 !important; font-weight: bold; }

    /* PRICE BOX STYLING */
    .price-container { font-size: 15px; font-weight: bold; margin-top: 4px; }
    .change-text { font-size: 11px; margin-left: 5px; opacity: 0.9; }

    /* LAYOUT COMPONENTS */
    .idx-card { background: #0e161f; border: 1px solid #1c2a38; border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
    .idx-left { display: flex; align-items: center; gap: 12px; }
    .idx-arrow { font-size: 20px; font-weight: bold; margin-top: -10px; }
    .idx-main-info { display: flex; flex-direction: column; gap: 2px; }
    .idx-name { font-size: 11px; color: #FFFFFF; font-weight: bold; text-transform: uppercase; }
    .idx-price { font-size: 18px; font-weight: bold; color: white; }
    .idx-right { text-align: right; display: flex; flex-direction: column; gap: 2px; font-weight: bold; margin-left: auto;}
    
    .grid-box { background-color: #0e161f; border: 1px solid #1c2a38; border-radius: 4px; padding: 10px; height: 140px; border-left: 3px solid #1c2a38; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
    .stock-row { background-color: #0e161f; padding: 12px; border-bottom: 1px solid #151f2b; display: flex; justify-content: space-between; align-items: flex-start; }
    .leader-header { background: #1c2a38; padding: 8px; border-radius: 6px; font-size: 13px; font-weight: bold; color: #ffd700; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .count-badge { background: #ffd700; color: #000; padding: 1px 6px; border-radius: 10px; font-size: 11px; }

    a { text-decoration: none !important; color: inherit; }
    div[data-testid="stTextInput"] { width: 180px !important; margin-left: auto; }
    </style>
    """, unsafe_allow_html=True)

# ============= [2] DATA ENGINE =============
def get_supertrend_list(df, period=9, multiplier=2):
    if len(df) < period: return [True] * len(df)
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2
    final_upperband = hl2 + (multiplier * atr)
    final_lowerband = hl2 - (multiplier * atr)
    st_list = [True] * len(df)
    for i in range(1, len(df)):
        if close.iloc[i] > final_upperband.iloc[i-1]: st_list[i] = True
        elif close.iloc[i] < final_lowerband.iloc[i-1]: st_list[i] = False
        else: st_list[i] = st_list[i-1]
    return st_list

def get_detailed_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news: return None
        latest = news[0]
        # IST Fix for news
        dt = datetime.fromtimestamp(latest['providerPublishTime'], tz=pytz.timezone('Asia/Kolkata'))
        time_str = dt.strftime("%d %b, %H:%M")
        title = latest['title'].lower()
        pos_words = ["profit", "up", "buy", "surge", "growth", "high", "gain", "order", "positive"]
        neg_words = ["loss", "down", "sell", "drop", "fall", "low", "dip", "negative", "penalty"]
        score = sum(1 for w in pos_words if w in title) - sum(1 for w in neg_words if w in title)
        return {"time": time_str, "sentiment": "POSITIVE" if score > 0 else ("NEGATIVE" if score < 0 else "NEUTRAL")}
    except: return None

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
            t_data = data[sym].dropna()
            cp, pcp = t_data['Close'].iloc[-1], t_data['Close'].iloc[-2]
            idx_res.append({'name': name, 'val': f"{cp:,.2f}", 'pts': round(cp-pcp, 2), 'pct': round(((cp-pcp)/pcp)*100, 2)})

        stock_res = []
        # Alert Date Key logic
        tz_ind = pytz.timezone('Asia/Kolkata')
        current_date = datetime.now(tz_ind).strftime("%Y%m%d")
        
        for s in stocks:
            t = s + ".NS"
            try:
                t_df = data[t].dropna()
                rsi_val = round(calculate_rsi(t_df['Close']).iloc[-1], 1)
                cp, pcp = t_df['Close'].iloc[-1], t_df['Close'].iloc[-2]
                hi, lo = t_df['High'].iloc[-2], t_df['Low'].iloc[-2]
                w_high = t_df['High'].iloc[-6:-1].max()
                v_ratio = round(t_df['Volume'].iloc[-1] / (t_df['Volume'].iloc[-6:-1].mean() + 1e-9), 2)
                
                w_trends = get_supertrend_list(t_df.resample('W').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna(), 9, 2)
                buy_switch = w_trends[-1] == True and w_trends[-2] == False
                sell_switch = w_trends[-1] == False and w_trends[-2] == True

                # ============= [TELEGRAM ALERTS] =============
                tv_link = f"https://www.tradingview.com/chart/?symbol=NSE:{s}"
                details = f"\nPrice: ₹{round(cp,2)}\nVol: x{v_ratio} | RSI: {rsi_val}\n<a href='{tv_link}'>📈 Open Chart</a>"
                
                if buy_switch:
                    send_telegram_msg(f"🏆 <b> BUY</b>: {s} @ ₹{round(cp,2)} 🟢{details}", f"{s}_{current_date}_buy")
                
                if sell_switch:
                    send_telegram_msg(f"🩸 <b> SELL</b>: {s} @ ₹{round(cp,2)} 🔴{details}", f"{s}_{current_date}_sell")
                
                if cp > hi and cp > w_high and v_ratio >= 2.0:
                    send_telegram_msg(f"🚀 <b>BREAKOUT BUY</b>: {s} @ ₹{round(cp,2)} 🟢{details}", f"{s}_{current_date}_break")

                tags_html = f'<div class="tag-container">'
                tags_html += f'<span class="tag-box tag-pdh">PDH</span>' if cp > hi else (f'<span class="tag-box tag-pdl">PDL</span>' if cp < lo else '<span class="tag-box tag-zone">ZONE</span>')
                if cp > w_high: tags_html += '<span class="tag-box tag-wb">WB</span>'
                tags_html += '</div>'

                stock_res.append({'Stock': s, 'LTP': round(cp, 2), 'Pts': round(cp-pcp, 2), 'Pct': round(((cp-pcp)/pcp)*100, 2), 'VolRatio': v_ratio, 'RSI': rsi_val, 'TagClass': 'PDH' if cp > hi else ('PDL' if cp < lo else 'ZONE'), 'FullTags': tags_html, 'Logo': f"https://s3-symbol-logo.tradingview.com/{s.lower()}--big.svg", 'BuySwitch': buy_switch, 'SellSwitch': sell_switch, 'WeeklyGreen': w_trends[-1]})
            except: continue
        return idx_res, pd.DataFrame(stock_res)
    except: return [], pd.DataFrame()

# ============= [3] UI STRUCTURE =============
h1, h2 = st.columns([3, 1])
with h1: st.title("🛡️ HEYFUND")
with h2:
    @st.fragment(run_every=1)
    def show_clock_live():
        # IST Fix
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        is_open = now.weekday() < 5 and (dt_time(9,15) <= now.time() <= dt_time(15,30))
        st.markdown(f'<div class="market-status-bar"><div class="status-dot {"dot-green" if is_open else "dot-red"}"></div><div class="{"status-badge" if is_open else "status-badge-closed"}">{"LIVE" if is_open else "CLOSED"}</div><div class="market-time">{now.strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)
    show_clock_live()

@st.fragment(run_every=60)
def show_dashboard_silent():
    # Anti-Sleep logic
    try: requests.get("https://google.com", timeout=1)
    except: pass

    indices, df = get_advanced_market_data()
    if indices:
        idx_cols = st.columns(4)
        for i, idx in enumerate(indices):
            color = "#00c853" if idx['pts'] >= 0 else "#ff5252"
            arrow = "↑" if idx['pts'] >= 0 else "↓"
            with idx_cols[i]:
                st.markdown(f"""
                    <div class="idx-card">
                        <div class="idx-left">
                            <div class="idx-arrow" style="color:{color};">{arrow}</div>
                            <div class="idx-main-info">
                                <span class="idx-name">{idx['name']}</span>
                                <span class="idx-price">{idx['val']}</span>
                            </div>
                        </div>
                        <div class="idx-right" style="color:{color};">
                            <span class="idx-pct">{idx['pct']}%</span>
                            <span class="idx-pts">{idx['pts']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)

    # Create tabs
    tab_lead, tab_all, tab_scan, tab_intraday = st.tabs(["🏆 LEADERS", "📋 ALL STOCKS", "🔍 SCANNER", "⚡ INTRADAY"])

    def draw_list_format(title, data, col):
        with col:
            st.markdown(f'<div class="leader-header"><span>{title}</span><span class="count-badge">{len(data.head(10))}</span></div>', unsafe_allow_html=True)
            for _, row in data.head(10).iterrows():
                color = "#00c853" if row['Pts'] > 0 else "#ff5252"
                v_class = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                st.markdown(f"""
                <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                    <div class="stock-row {"pdh-alert" if row["TagClass"]=="PDH" else ""}">
                        <div style="display:flex; align-items:flex-start;">
                            <img src="{row['Logo']}" style="width:20px; border-radius:50%; margin-right:10px; margin-top:4px;">
                            <div><b style="color:white;">{row['Stock']}</b>{row['FullTags']}<br>
                            <div class="price-container" style="color:{color};">₹{row['LTP']} <span class="change-text">({'+' if row['Pts']>0 else ''}{row['Pts']} {row['Pct']}%)</span></div></div>
                        </div>
                        <div style="text-align:right;" class="{v_class}">x{row['VolRatio']} Vol</div>
                    </div>
                </a>""", unsafe_allow_html=True)

    with tab_lead:
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            draw_list_format("GAINERS", df[df['Pts'] > 0].sort_values('Pct', ascending=False), c1)
            draw_list_format("LOSERS", df[df['Pts'] < 0].sort_values('Pct', ascending=True), c2)
            draw_list_format("VOL SHOCKERS", df.sort_values(by=['Pts', 'VolRatio'], ascending=[False, False]), c3)

    with tab_all:
        s_term = st.text_input("🔍 Search Symbols...", value="", key="search_bar").upper()
        if not df.empty:
            f_df = df[df['Stock'].str.contains(s_term)] if s_term else df
            g_cols = st.columns(7)
            for i, (idx, row) in enumerate(f_df.iterrows()):
                color = "#00c853" if row['Pts'] > 0 else "#ff5252"
                v_class = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                with g_cols[i % 7]:
                    st.markdown(f"""
                        <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                            <div class="grid-box {"pdh-alert" if row["TagClass"]=="PDH" else ""}" style="border-left:3px solid {color}; margin-bottom:10px;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-size:11px; font-weight:bold; color:#8a99a8;">{row['Stock']}</span>{row['FullTags']}
                                </div>
                                <div class="price-container" style="color:{color};">₹{row['LTP']}<br><span class="change-text" style="margin-left:0;">{'+' if row['Pts']>0 else ''}{row['Pts']} ({row['Pct']}%)</span></div>
                                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1c2a38; padding-top:4px; font-size:10px;">
                                    <span class="{v_class}">x{row['VolRatio']} V</span><span class="rsi-text-yellow">RSI:{row['RSI']}</span>
                                </div>
                            </div>
                        </a>""", unsafe_allow_html=True)

    with tab_scan:
        if not df.empty:
            s1, s2, s3, s4 = st.columns(4)
            draw_list_format("🏆 BUY", df[df['BuySwitch'] == True], s1)
            draw_list_format("🩸 SELL", df[df['SellSwitch'] == True], s2)
            draw_list_format("💪 STRONG BUY", df[(df['WeeklyGreen'] == True) & (df['RSI'] > 60)], s3)
            draw_list_format("🚀 BREAKOUT", df[df['VolRatio'] >= 1.8].sort_values('VolRatio', ascending=False), s4)

    with tab_intraday:
        if not df.empty:
            st.markdown("### ⚡ INTRADAY SIGNALS")
            
            # Calculate counts
            bullish_count = len(df[df['TagClass'] == 'PDH'])
            bearish_count = len(df[df['TagClass'] == 'PDL'])
            neutral_count = len(df[df['TagClass'] == 'ZONE'])
            
            # Create 3 expandable sections with counts only
            with st.expander(f"🟢 BULLISH ({bullish_count})", expanded=True):
                bullish_df = df[df['TagClass'] == 'PDH'].sort_values('VolRatio', ascending=False)
                
                if not bullish_df.empty:
                    g_cols_bull = st.columns(7)
                    for i, (idx, row) in enumerate(bullish_df.iterrows()):
                        color = "#00c853"
                        v_class = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                        with g_cols_bull[i % 7]:
                            st.markdown(f"""
                                <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                                    <div class="grid-box pdh-alert" style="border-left:3px solid {color}; margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; align-items:center;">
                                            <span style="font-size:11px; font-weight:bold; color:#8a99a8;">{row['Stock']}</span>{row['FullTags']}
                                        </div>
                                        <div class="price-container" style="color:{color};">₹{row['LTP']}<br><span class="change-text" style="margin-left:0;">{'+' if row['Pts']>0 else ''}{row['Pts']} ({row['Pct']}%)</span></div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1c2a38; padding-top:4px; font-size:10px;">
                                            <span class="{v_class}">x{row['VolRatio']} V</span><span class="rsi-text-yellow">RSI:{row['RSI']}</span>
                                        </div>
                                    </div>
                                </a>""", unsafe_allow_html=True)
                else:
                    st.info("No BULLISH stocks found")
            
            with st.expander(f"🔴 BEARISH ({bearish_count})", expanded=True):
                bearish_df = df[df['TagClass'] == 'PDL'].sort_values('VolRatio', ascending=False)
                
                if not bearish_df.empty:
                    g_cols_bear = st.columns(7)
                    for i, (idx, row) in enumerate(bearish_df.iterrows()):
                        color = "#ff5252"
                        v_class = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                        with g_cols_bear[i % 7]:
                            st.markdown(f"""
                                <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                                    <div class="grid-box" style="border-left:3px solid {color}; margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; align-items:center;">
                                            <span style="font-size:11px; font-weight:bold; color:#8a99a8;">{row['Stock']}</span>{row['FullTags']}
                                        </div>
                                        <div class="price-container" style="color:{color};">₹{row['LTP']}<br><span class="change-text" style="margin-left:0;">{'+' if row['Pts']>0 else ''}{row['Pts']} ({row['Pct']}%)</span></div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1c2a38; padding-top:4px; font-size:10px;">
                                            <span class="{v_class}">x{row['VolRatio']} V</span><span class="rsi-text-yellow">RSI:{row['RSI']}</span>
                                        </div>
                                    </div>
                                </a>""", unsafe_allow_html=True)
                else:
                    st.info("No BEARISH stocks found")
            
            with st.expander(f"⚪ NEUTRAL ({neutral_count})", expanded=True):
                neutral_df = df[df['TagClass'] == 'ZONE'].sort_values('VolRatio', ascending=False)
                
                if not neutral_df.empty:
                    g_cols_neu = st.columns(7)
                    for i, (idx, row) in enumerate(neutral_df.iterrows()):
                        color = "#888888" if row['Pts'] == 0 else ("#00c853" if row['Pts'] > 0 else "#ff5252")
                        v_class = "vol-text-green" if row['VolRatio'] >= 2.0 else ""
                        with g_cols_neu[i % 7]:
                            st.markdown(f"""
                                <a href="https://www.tradingview.com/chart/?symbol=NSE:{row['Stock']}" target="_blank">
                                    <div class="grid-box" style="border-left:3px solid {color}; margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; align-items:center;">
                                            <span style="font-size:11px; font-weight:bold; color:#8a99a8;">{row['Stock']}</span>{row['FullTags']}
                                        </div>
                                        <div class="price-container" style="color:{color};">₹{row['LTP']}<br><span class="change-text" style="margin-left:0;">{'+' if row['Pts']>0 else ''}{row['Pts']} ({row['Pct']}%)</span></div>
                                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1c2a38; padding-top:4px; font-size:10px;">
                                            <span class="{v_class}">x{row['VolRatio']} V</span><span class="rsi-text-yellow">RSI:{row['RSI']}</span>
                                        </div>
                                    </div>
                                </a>""", unsafe_allow_html=True)
                else:
                    st.info("No NEUTRAL stocks found")

show_dashboard_silent()
