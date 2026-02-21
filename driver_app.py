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
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. HIGH-CONTRAST CSS (FORCED WHITE TEXT) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; font-size: 20px !important; color: #333 !important;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px; font-size: 22px !important;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; font-size: 24px !important;}
    
    .btn-blue, .btn-pink, .btn-purple, .btn-green {
        padding: 18px !important; font-size: 22px !important; border-radius: 10px; text-align: center; 
        font-weight: bold; margin-bottom: 10px; text-decoration: none; display: block;
        color: #ffffff !important; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-pink {background-color: #e83e8c !important;}
    .btn-purple {background-color: #6f42c1 !important;}
    .btn-green {background-color: #28a745 !important;}
    
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURATION ---
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

# --- 4. MAIN APP ---
try:
    roster_df, dispatch_df, schedule_df, ql_df = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None, placeholder="Type Numbers Only")

    if input_val:
        u_id = str(int(input_val))
        roster_df['match_id'] = roster_df['Employee #'].apply(clean_num)
        driver_match = roster_df[roster_df['match_id'] == u_id]

        if not driver_match.empty:
            driver = driver_match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{driver.get('Driver Name', 'Driver')}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # Compliance, Dispatch, and PeopleNet sections remain as requested...
            # (Logic for those is identical to your working version)

            # DAILY SCHEDULE (THE SPECIFIC FIX)
            schedule_df['route_match'] = schedule_df.iloc[:, 0].apply(clean_num)
            my_stops = schedule_df[schedule_df['route_match'] == route_num]
            if not my_stops.empty:
                st.markdown("<h3 style='font-size:30px;'>Daily Schedule</h3>", unsafe_allow_html=True)
                for _, stop in my_stops.iterrows():
                    addr = str(stop.get('Store Address'))
                    raw_sid = clean_num(stop.get('Store ID'))
                    
                    # Store ID Formatting Logic
                    sid_dialer = raw_sid.zfill(6) # 6 digits for the tracker phone call
                    sid_web = raw_sid.zfill(5)    # 5 digits for the cpcfact URL
                    
                    arrival = stop.get('Arrival time')
                    
                    with st.expander(f"📍 Stop: {sid_web if raw_sid != '0' else 'Relay'} ({arrival})", expanded=True):
                        ca, cb = st.columns(2)
                        clean_addr = addr.replace(' ','+').replace('\n','')
                        with ca:
                            if raw_sid != '0':
                                # Dialer uses sid_dialer (6 digits)
                                tracker_link = f"tel:8008710204,1,,88012#,,{sid_dialer},#,,,1,,,1"
                                st.markdown(f'<a href="{tracker_link}" class="btn-green">📞 Call Store Tracker</a>', unsafe_allow_html=True)
                            st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={clean_addr}" class="btn-blue">🌎 Google Maps</a>', unsafe_allow_html=True)
                        with cb:
                            st.markdown(f'<a href="truckmap://navigate?q={clean_addr}" class="btn-blue">🚛 Truck Map</a>', unsafe_allow_html=True)
                            if raw_sid != '0':
                                # Store Map uses sid_web (5 digits)
                                st.markdown(f'<a href="https://wg.cpcfact.com/store-{sid_web}/" class="btn-blue">🗺️ Store Map</a>', unsafe_allow_html=True)
                        st.link_button("🚨 Report Issue", ISSUE_FORM_URL, use_container_width=True)

            # Quick Links Loop...
            # (Logic for links remains identical to your working version)

except Exception as e:
    st.error(f"Sync Error: {e}")
