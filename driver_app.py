import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. ANDROID INSTALL LOGIC (PWA) ---
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

# --- 2. HIGH-CONTRAST CSS (LOCKING BUTTON VISIBILITY) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; color: #333 !important;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    
    /* THE BUTTON FIX */
    .btn-blue, .btn-pink, .btn-purple, .btn-green, .btn-red {
        padding: 18px !important; 
        font-size: 22px !important; 
        border-radius: 10px; 
        text-align: center; 
        font-weight: bold; 
        margin-bottom: 12px; 
        text-decoration: none !important; 
        display: block;
        color: #ffffff !important; 
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2);
        border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-pink {background-color: #e83e8c !important;}
    .btn-purple {background-color: #6f42c1 !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURATION & DATA ---
ISSUE_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"

@st.cache_data(ttl=5) 
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    roster_gid, schedule_gid, dispatch_gid, ql_gid = "1261782560", "1908585361", "1123038440", "489255872"
    def get_sheet(gid):
        url = f"{base_url}&gid={gid}&cache_bust={int(time.time())}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_sheet(roster_gid), get_sheet(dispatch_gid), get_sheet(schedule_gid), get_sheet(ql_gid)

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
    roster_df, dispatch_df, schedule_df, ql_df = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None, placeholder="Numbers Only")

    if input_val:
        u_id = str(int(input_val))
        roster_df['match_id'] = roster_df['Employee #'].apply(clean_num)
        driver_match = roster_df[roster_df['match_id'] == u_id]

        if not driver_match.empty:
            driver = driver_match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{driver.get('Driver Name', 'Driver')}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # Compliance section
            dot_count, _ = driver.get('DOT Physical Expires'), "" # Simplified for clarity
            cdl_count = driver.get('DL Expiration Date')
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(dot_count)}</span></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(cdl_count)}</span></div>", unsafe_allow_html=True)

            # Dispatch section
            dispatch_df['route_match'] = dispatch_df.iloc[:, 0].apply(clean_num)
            d_info = dispatch_df[dispatch_df['route_match'] == route_num]
            if not d_info.empty:
                st.markdown(f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400;'>DISPATCH NOTES</h3><div style='font-size:24px; font-weight:bold;'>{d_info.iloc[0].get('Comments', 'None')}</div></div>", unsafe_allow_html=True)

            # Daily Schedule
            schedule_df['route_match'] = schedule_df.iloc[:, 0].apply(clean_num)
            my_stops = schedule_df[schedule_df['route_match'] == route_num]
            if not my_stops.empty:
                st.markdown("<h3 style='font-size:30px;'>Daily Schedule</h3>", unsafe_allow_html=True)
                for _, stop in my_stops.iterrows():
                    raw_sid = clean_num(stop.get('Store ID'))
                    sid_6 = raw_sid.zfill(6) 
                    sid_5 = raw_sid.zfill(5) 
                    clean_addr = str(stop.get('Store Address')).replace(' ','+').replace('\n','')
                    
                    with st.expander(f"📍 Stop: {sid_5 if raw_sid != '0' else 'Relay'}", expanded=True):
                        st.write(f"**Address:** {stop.get('Store Address')}")
                        
                        # --- THE FIXED BUTTON BLOCK ---
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if raw_sid != '0':
                                st.markdown(f'<a href="tel:8008710204,1,,88012#,,{sid_6},#,,,1,,,1" class="btn-green">📞 Call Store Tracker</a>', unsafe_allow_html=True)
                            st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={clean_addr}" class="btn-blue">🌎 Google Maps</a>', unsafe_allow_html=True)
                        with col_b:
                            st.markdown(f'<a href="truckmap://navigate?q={clean_addr}" class="btn-blue">🚛 Truck Map</a>', unsafe_allow_html=True)
                            if raw_sid != '0':
                                # This is the hard-coded "Store Map" button fix
                                st.markdown(f'<a href="https://wg.cpcfact.com/store-{sid_5}/" class="btn-blue">🗺️ Store Map</a>', unsafe_allow_html=True)
                        
                        st.markdown(f'<a href="{ISSUE_FORM_URL}" class="btn-red">🚨 Report Issue</a>', unsafe_allow_html=True)

            # Quick Links
            st.divider()
            for _, link in ql_df.iterrows():
                name, val = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if val != "nan" and val != "":
                    if "elba" in name.lower():
                        st.markdown(f'<a href="mailto:{val}" class="btn-pink">✉️ Email {name}</a>', unsafe_allow_html=True)
                    elif "http" not in val and any(c.isdigit() for c in val):
                        st.markdown(f'<a href="tel:{re.sub(r"[^0-9]", "", val)}" class="btn-purple">📞 Call {name}</a>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<a href="{val}" target="_blank" class="btn-blue">🔗 {name}</a>', unsafe_allow_html=True)
        else:
            st.error("Employee ID not found.")
except Exception as e:
    st.error(f"Sync Error: {e}")
