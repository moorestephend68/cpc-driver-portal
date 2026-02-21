import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. THE "APP" INSTALLER LOGIC (FOR ANDROID) ---
# This forces Chrome to see the 'Install App' option
manifest_json = """
{
  "name": "CPC Driver Portal",
  "short_name": "CPC Portal",
  "start_url": ".",
  "display": "standalone",
  "theme_color": "#004a99",
  "background_color": "#ffffff",
  "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2554/2554979.png", "sizes": "512x512", "type": "image/png"}]
}
"""
manifest_base64 = base64.b64encode(manifest_json.encode()).decode()

st.set_page_config(page_title="CPC Driver Portal", layout="centered", page_icon="🚛")

# Injecting the manifest into the browser header
st.markdown(f"""
    <head>
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. THE VISIBILITY FIX (FORCED BACKGROUNDS & WHITE TEXT) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    
    /* Solid Header */
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    
    /* Card Styles */
    .badge-info {background-color: #f0f2f6 !important; padding: 15px; border-radius: 8px; text-align: center; height: 100%; color: #004a99 !important;}
    .val {display: block; font-weight: bold; font-size: 26px !important;}
    
    /* BUTTONS: Forced Solid Backgrounds with White Text */
    .btn-custom {
        padding: 18px !important; 
        font-size: 22px !important; 
        border-radius: 10px; 
        text-align: center; 
        font-weight: bold; 
        margin-bottom: 10px; 
        text-decoration: none; 
        display: block;
        color: #ffffff !important; /* FORCED WHITE TEXT */
    }
    
    /* Assigned Colors */
    .bg-blue {background-color: #007bff !important;}   /* Maps/Links */
    .bg-pink {background-color: #e83e8c !important;}   /* Elba/Email */
    .bg-purple {background-color: #6f42c1 !important;} /* Calls */
    .bg-green {background-color: #28a745 !important;}  /* Tracker */
    .bg-red {background-color: #dc3545 !important;}    /* Report Issue */

    input { font-size: 26px !important; height: 65px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOADING DATA ---
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

# --- APP EXECUTION ---
try:
    roster_df, dispatch_df, schedule_df, ql_df = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None)

    if input_val:
        u_id = str(int(input_val))
        roster_df['match_id'] = roster_df['Employee #'].apply(clean_num)
        driver_match = roster_df[roster_df['match_id'] == u_id]

        if not driver_match.empty:
            driver = driver_match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            
            st.markdown(f"<div class='header-box'><b>{driver.get('Driver Name', 'Driver')}</b><br>ID: {u_id} | Route: {route_num}</div>", unsafe_allow_html=True)

            # Schedule Section
            schedule_df['route_match'] = schedule_df.iloc[:, 0].apply(clean_num)
            my_stops = schedule_df[schedule_df['route_match'] == route_num]
            
            if not my_stops.empty:
                for _, stop in my_stops.iterrows():
                    addr = str(stop.get('Store Address'))
                    sid = clean_num(stop.get('Store ID')).zfill(5)
                    with st.expander(f"📍 Stop: {sid} ({stop.get('Arrival time')})", expanded=True):
                        ca, cb = st.columns(2)
                        clean_addr = addr.replace(' ','+').replace('\n','')
                        with ca:
                            if sid != '00000':
                                tracker_num = f"tel:8008710204,1,,88012#,,{sid},#,,,1,,,1"
                                st.markdown(f'<a href="{tracker_num}" class="btn-custom bg-green">📞 Tracker</a>', unsafe_allow_html=True)
                            st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={clean_addr}" class="btn-custom bg-blue">🌎 Google</a>', unsafe_allow_html=True)
                        with cb:
                            st.markdown(f'<a href="truckmap://navigate?q={clean_addr}" class="btn-custom bg-blue">🚛 TruckMap</a>', unsafe_allow_html=True)
                            if sid != '00000':
                                st.markdown(f'<a href="https://wg.cpcfact.com/store-{sid}/" class="btn-custom bg-blue">🗺️ Map</a>', unsafe_allow_html=True)
                        
                        st.markdown(f'<a href="{ISSUE_FORM_URL}" class="btn-custom bg-red">🚨 Report Issue</a>', unsafe_allow_html=True)

            # Quick Links
            st.divider()
            for _, link in ql_df.iterrows():
                name, val = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if val != "nan" and val != "":
                    if "elba" in name.lower():
                        st.markdown(f'<a href="mailto:{val}" class="btn-custom bg-pink">✉️ Email {name}</a>', unsafe_allow_html=True)
                    elif "http" not in val and any(c.isdigit() for c in val):
                        st.markdown(f'<a href="tel:{re.sub(r"[^0-9]", "", val)}" class="btn-custom bg-purple">📞 Call {name}</a>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<a href="{val}" target="_blank" class="btn-custom bg-blue">🔗 {name}</a>', unsafe_allow_html=True)
        else:
            st.error("Employee ID not found.")
except Exception as e:
    st.error(f"Error: {e}")
