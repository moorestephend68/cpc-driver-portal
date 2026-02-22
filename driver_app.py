import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. ANDROID INSTALL LOGIC ---
manifest_json = """
{
  "name": "CPC Driver Portal",
  "short_name": "CPC Portal",
  "start_url": "https://cpc-driver.streamlit.app/",
  "display": "standalone",
  "theme_color": "#004a99",
  "background_color": "#ffffff",
  "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2554/2554979.png", "sizes": "512x512", "type": "image/png"}]
}
"""
manifest_base64 = base64.b64encode(manifest_json.encode()).decode()

st.set_page_config(page_title="CPC Driver Portal", layout="centered", page_icon="🚛")

st.markdown(f"""
    <head>
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px;}
    
    a.btn-blue, a.btn-green, a.btn-pink, a.btn-purple, a.btn-red {
        display: block !important; width: 100% !important; padding: 18px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 19px !important; text-decoration: none !important; color: #ffffff !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important; margin-top: 10px !important;}
    
    #store-map-btn { background-color: #007bff !important; color: white !important; }
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOADING WITH FORCE REFRESH ---
@st.cache_data(ttl=5) # Mechanism 1: 5-second TTL
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    
    def get_sheet(gid):
        # Mechanism 2: Cache-busting query parameter
        url = f"{base_url}&gid={gid}&cb={int(time.time())}" 
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
        
    return get_sheet(gids["roster"]), get_sheet(gids["dispatch"]), get_sheet(gids["schedule"]), get_sheet(gids["links"])

# --- HELPERS ---
def clean_num(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def format_date(date_str):
    if pd.isna(date_str) or not str(date_str).strip(): return "N/A"
    try:
        dt = pd.to_datetime(date_str, errors='coerce')
        return dt.strftime("%B %d, %Y") if not pd.isna(dt) else str(date_str)
    except: return str(date_str)

# --- 4. MAIN APP ---
try:
    # Mechanism 3: Manual Refresh Button
    if st.button("🔄 Sync New Dispatch Data"):
        st.cache_data.clear()
        st.rerun()

    roster, dispatch, schedule, links = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None)

    if input_val:
        u_id = str(int(input_val))
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == u_id]

        if not match.empty:
            driver = match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            d_name = driver.get('Driver Name', driver.iloc[0])
            
            st.markdown(f"<div class='header-box'><div style='font-size:36px; font-weight:bold;'>{d_name}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # DISPATCH NOTES (Primary target for refresh)
            dispatch['route_match'] = dispatch.iloc[:, 0].apply(clean_num)
            d_info = dispatch[dispatch['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                st.markdown(f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400; font-size:18px;'>DISPATCH NOTES</h3><div style='font-size:24px; font-weight:bold; color:#d35400;'>{r_data.get('Comments', 'None')}</div><div style='margin-top:10px;'><b>Trailers:</b> {r_data.get('1st Trailer')} / {r_data.get('2nd Trailer')}</div></div>", unsafe_allow_html=True)

            # (Rest of schedule and links sections remain identical to your working version)
            # ... [Schedule logic continues here] ...
            
except Exception as e:
    st.error(f"Sync Error: {e}")
