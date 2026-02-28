import streamlit as st
import pandas as pd
import re
import time
import urllib.parse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh 

# --- 1. CONFIG & REFRESH ---
st_autorefresh(interval=60000, key="datarefresh")
st.set_page_config(page_title="CPC Portal", layout="centered", page_icon="🚛")

# --- 2. GLOBAL STYLES ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 20px; border-radius: 12px; margin-bottom: 15px;}
    
    .safety-box {
        background-color: #fff4f4 !important;
        border: 3px solid #cc0000 !important;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        color: #1a1a1a !important;
    }
    .safety-box h2 { color: #cc0000 !important; margin-top: 0; font-size: 22px; }

    /* Green Confirmation Button */
    .btn-confirm {
        display: block !important; width: 100% !important; padding: 20px 0px !important;
        border-radius: 12px !important; text-align: center !important; font-weight: bold !important;
        font-size: 20px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 15px !important; background-color: #107c10 !important; border: 2px solid #ffffff !important;
    }

    /* Blue Already-Confirmed Button */
    .btn-done {
        display: block !important; width: 100% !important; padding: 20px 0px !important;
        border-radius: 12px !important; text-align: center !important; font-weight: bold !important;
        font-size: 20px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 15px !important; background-color: #007bff !important; border: 2px solid #ffffff !important;
    }

    .stop-detail-card {
        background-color: #f0f2f6 !important; 
        color: #1a1a1a !important; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 12px; 
        border-left: 6px solid #004a99 !important;
    }

    .btn-blue, .btn-green, .btn-red {
        display: block !important; width: 100% !important; padding: 15px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 18px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 10px !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    
    input { font-size: 22px !important; height: 55px !important; color: #000 !important; background-color: #fff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HELPERS ---
def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def safe_get(row, col_name, index, default=""):
    if col_name in row: return str(row[col_name]).strip()
    if len(row) > index: return str(row.iloc[index]).strip()
    return default

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872", "safety": "1978744657"}
    def get_s(gid):
        try:
            df = pd.read_csv(f"{base_url}&gid={gid}&cb={int(time.time())}", low_memory=False)
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return get_s(gids["roster"]), get_s(gids["dispatch"]), get_s(gids["schedule"]), get_s(gids["links"]), get_s(gids["safety"])

# --- 4. MAIN APP ---
try:
    roster, dispatch_notes_df, schedule, quick_links, safety_df = load_all_data()
    st.markdown("<h1 style='font-size: 28px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)

    user_input = st.text_input("Enter ID", value="").strip().lower()

    if user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            d_name = safe_get(driver, 'Driver Name', 0)
            raw_route = str(driver.get('Route', ''))
            route_num = clean_num(raw_route)

            # --- SAFETY MESSAGE ---
            today_str = datetime.now().strftime("%m/%d/%Y")
            safety_msg = "Perform a thorough pre-trip inspection."
            if not safety_df.empty:
                s_match = safety_df[safety_df.iloc[:, 0].astype(str).str.contains(today_str, na=False)]
                if not s_match.empty: safety_msg = s_match.iloc[0, 1]
            
            st.markdown(f"<div class='safety-box'><h2>⚠️ DAILY SAFETY REMINDER</h2><p>{safety_msg}</p></div>", unsafe_allow_html=True)

            # --- CONFIRMATION TOGGLE & COLOR-CHANGING BUTTON ---
            confirm_key = f"confirmed_{user_input}"
            is_confirmed = st.toggle("I have submitted the Route Confirmation Form", key=confirm_key)

            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfnw_F7nGy4GbJlMlCxSSGXx86b8g5J6VhXRkz_ZvABr2fcMg/viewform?"
            params = {"entry.534103007": d_name, "entry.726947479": user_input, "entry.316322786": raw_route}
            full_url = form_url + urllib.parse.urlencode(params)

            if not is_confirmed:
                st.markdown(f'<a href="{full_url}" target="_blank" class="btn-confirm">🚛 READ SAFETY & CONFIRM ROUTE</a>', unsafe_allow_html=True)
            else:
                st.markdown(f'<a href="{full_url}" target="_blank" class="btn-done">✅ ROUTE CONFIRMED - OPEN FORM AGAIN</a>', unsafe_allow_html=True)

            # Portal Header
            st.markdown(f"<div class='header-box'><h3>{d_name}</h3>Route: {raw_route}</div>", unsafe_allow_html=True)

            # Schedule & Restored Feedback Button
            st.markdown("### Daily Schedule")
            if route_num:
                schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                my_stops = schedule[schedule['route_match'] == route_num]
                for _, stop in my_stops.iterrows():
                    sid = clean_num(safe_get(stop, 'Store ID', 4))
                    addr = safe_get(stop, 'Store Address', 5)
                    with st.expander(f"📍 Store {sid}"):
                        st.markdown(f"<div class='stop-detail-card'><b>Address:</b><br>{addr}</div>", unsafe_allow_html=True)
                        
                        tracker_url = f"tel:8008710204,1,,88012#,,{sid},#,,,1,,,1"
                        issue_url = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"
                        
                        st.markdown(f"<a href='{tracker_url}' class='btn-green'>📞 Store Tracker</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='https://www.google.com/maps/search/?api=1&query={addr.replace(' ','+')}' class='btn-blue'>🌎 Google Maps</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{issue_url}' class='btn-red'>🚨 Report Issue (Feedback)</a>", unsafe_allow_html=True)
            
            st.divider()
            for _, link in quick_links.iterrows():
                n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                st.markdown(f"<a href='{v}' class='btn-blue'>{n}</a>", unsafe_allow_html=True)

        else: st.error("ID not found.")
except Exception as e: st.error(f"Error: {e}")
