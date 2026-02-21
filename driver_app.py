import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. ANDROID INSTALL LOGIC (PWA) ---
# Hardcoding the manifest for https://cpc-driver.streamlit.app/
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

# --- 2. HIGH-CONTRAST CSS (FORCED WHITE TEXT) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background-color: #f0f2f6 !important; padding: 15px; border-radius: 8px; text-align: center; color: #004a99 !important; border: 1px solid #ddd;}
    .val {display: block; font-weight: bold; font-size: 26px !important; color: #004a99 !important;}
    .dispatch-box {border: 3px solid #d35400; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    
    .btn-custom {
        padding: 18px !important; font-size: 22px !important; border-radius: 10px; text-align: center; 
        font-weight: bold; margin-bottom: 10px; text-decoration: none; display: block;
        color: white !important; /* FIXED: Always White for Android visibility */
    }
    .bg-blue {background-color: #007bff !important;}
    .bg-pink {background-color: #e83e8c !important;}
    .bg-purple {background-color: #6f42c1 !important;}
    .bg-green {background-color: #28a745 !important;}
    .bg-red {background-color: #dc3545 !important;}
    
    input { font-size: 26px !important; height: 65px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ROBUST DATA LOADING ---
@st.cache_data(ttl=2) 
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    
    def get_df(gid):
        url = f"{base_url}&gid={gid}&cache_bust={time.time()}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df

    return get_df(gids["roster"]), get_df(gids["dispatch"]), get_df(gids["schedule"]), get_df(gids["links"])

def clean(val):
    if pd.isna(val): return ""
    return re.sub(r'\D', '', str(val))

# --- 4. MAIN APP ---
try:
    roster, dispatch, schedule, links = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    user_input = st.text_input("Enter Employee ID", placeholder="Numbers only")

    if user_input:
        u_id = clean(user_input)
        
        # KEY FIX: Searching for the ID column by keyword instead of position
        id_col = next((c for c in roster.columns if any(k in c for k in ['Employee', 'ID', '#'])), roster.columns[0])
        roster['match_id'] = roster[id_col].apply(clean)
        match = roster[roster['match_id'] == u_id]

        if not match.empty:
            driver = match.iloc[0]
            # Find Route Column
            rt_col = next((c for c in roster.columns if 'Route' in c), roster.columns[0])
            route_num = clean(driver[rt_col])
            
            # HEADER
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{driver.iloc[0]}</div><div style='font-size:22px;'>Route: {route_num}</div></div>", unsafe_allow_html=True)

            # COMPLIANCE (Dynamic Column Search)
            dot_col = next((c for c in roster.columns if 'DOT' in c), None)
            cdl_col = next((c for c in roster.columns if any(k in c for k in ['DL', 'CDL'])), None)
            
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Expires<span class='val'>{driver.get(dot_col, 'N/A')}</span></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Expires<span class='val'>{driver.get(cdl_col, 'N/A')}</span></div>", unsafe_allow_html=True)

            # DISPATCH SECTION
            dispatch['r_match'] = dispatch.iloc[:, 0].apply(clean)
            d_data = dispatch[dispatch['r_match'] == route_num]
            if not d_data.empty:
                comment = d_data.iloc[0].get('Comments', 'No notes')
                st.markdown(f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400;'>DISPATCH</h3><div style='font-size:24px; font-weight:bold;'>{comment}</div></div>", unsafe_allow_html=True)

            # ROUTING SECTION
            schedule['r_match'] = schedule.iloc[:, 0].apply(clean)
            my_stops = schedule[schedule['r_match'] == route_num]
            
            if not my_stops.empty:
                st.markdown("<h3 style='font-size:30px;'>Daily Stops</h3>", unsafe_allow_html=True)
                for _, stop in my_stops.iterrows():
                    sid_raw = stop.get('Store ID', '00000')
                    sid = clean(sid_raw).zfill(5)
                    addr = stop.get('Store Address', 'No Address')
                    with st.expander(f"📍 Stop: {sid}", expanded=True):
                        st.write(f"**Address:** {addr}")
                        ca, cb = st.columns(2)
                        with ca:
                            st.markdown(f'<a href="tel:8008710204,1,,88012#,,{sid}" class="btn-custom bg-green">📞 Tracker</a>', unsafe_allow_html=True)
                        with cb:
                            st.markdown(f'<a href="https://wg.cpcfact.com/store-{sid}/" class="btn-custom bg-blue">🗺️ Store Map</a>', unsafe_allow_html=True)

            # QUICK LINKS SECTION
            st.divider()
            st.subheader("🔗 Quick Links")
            for _, link in links.iterrows():
                l_name = str(link.iloc[0])
                l_val = str(link.iloc[1])
                if "http" in l_val:
                    st.markdown(f'<a href="{l_val}" class="btn-custom bg-blue">{l_name}</a>', unsafe_allow_html=True)
                elif "@" in l_val:
                    st.markdown(f'<a href="mailto:{l_val}" class="btn-custom bg-pink">✉️ Email {l_name}</a>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<a href="tel:{clean(l_val)}" class="btn-custom bg-purple">📞 Call {l_name}</a>', unsafe_allow_html=True)
        else:
            st.error("ID Not Found. Please check the number.")
            if st.checkbox("Show Diagnostics"):
                st.write("Current Columns:", roster.columns.tolist())

except Exception as e:
    st.error(f"Error: {e}")
