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

# --- 2. GLOBAL STYLES (High Contrast & Cross-Platform Fixes) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    
    .safety-box {
        background-color: #fff4f4 !important;
        border: 3px solid #cc0000 !important;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        color: #1a1a1a !important;
    }
    .safety-box h2 { color: #cc0000 !important; margin-top: 0; font-size: 22px; }
    
    .btn-confirm {display: block !important; width: 100% !important; padding: 20px 0px !important; border-radius: 12px !important; text-align: center !important; font-weight: bold !important; font-size: 20px !important; text-decoration: none !important; color: white !important; margin-bottom: 15px !important; background-color: #107c10 !important; border: 2px solid #ffffff !important;}
    .btn-done {display: block !important; width: 100% !important; padding: 20px 0px !important; border-radius: 12px !important; text-align: center !important; font-weight: bold !important; font-size: 20px !important; text-decoration: none !important; color: white !important; margin-bottom: 15px !important; background-color: #007bff !important; border: 2px solid #ffffff !important;}
    
    .stop-detail-card {background-color: #f0f2f6 !important; color: #1a1a1a !important; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #004a99 !important;}
    .dispatch-box {border: 2px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 20px; color: #1a1a1a !important;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 24px;}
    
    .eld-card {background-color: #2c3e50 !important; color: #ffffff !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid #34495e;}
    .eld-val {color: #3498db !important; font-size: 26px; font-weight: bold; font-family: monospace;}
    
    .btn-blue, .btn-green, .btn-red {display: block !important; width: 100% !important; padding: 15px 0px !important; border-radius: 10px !important; text-align: center !important; font-weight: bold !important; font-size: 18px !important; text-decoration: none !important; color: white !important; margin-bottom: 10px !important; border: none !important; text-decoration: none !important;}
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    
    input { font-size: 24px !important; height: 60px !important; color: #000000 !important; background-color: #ffffff !important; -webkit-text-fill-color: #000000 !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. HELPERS ---
def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_id_alphanumeric(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return str(val).strip()

def format_date(date_str):
    if pd.isna(date_str) or not str(date_str).strip(): return "N/A"
    try:
        dt = pd.to_datetime(date_str, errors='coerce')
        return dt.strftime("%B %d, %Y") if not pd.isna(dt) else str(date_str)
    except: return str(date_str)

def get_renewal_status(exp_date_val):
    if pd.isna(exp_date_val): return "N/A", ""
    try:
        exp_date = pd.to_datetime(exp_date_val)
        diff = relativedelta(exp_date, datetime.now())
        days_left = (exp_date - datetime.now()).days
        return f"{diff.years}y {diff.months}m {diff.days}d", ("⚠️ RENEW NOW" if days_left <= 60 else "")
    except: return "N/A", ""

def calculate_tenure(hire_date_val):
    if pd.isna(hire_date_val): return "N/A"
    try:
        hire_date = pd.to_datetime(hire_date_val)
        diff = relativedelta(datetime.now(), hire_date)
        return f"{hire_date.strftime('%B %d, %Y')} ({diff.years} yrs, {diff.months} mos)"
    except: return str(hire_date_val)

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

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard")
        responses_url = "https://docs.google.com/spreadsheets/d/1yGwaBQaciW6F0MTlHSTgx1ozp00nULTNApctZYtBOAU/edit?usp=sharing"
        st.markdown(f'<a href="{responses_url}" target="_blank" class="btn-confirm" style="background-color: #004a99 !important;">📊 VIEW LIVE ROUTE CONFIRMATIONS</a>', unsafe_allow_html=True)
        st.info("Dispatcher access granted.")

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            d_name = safe_get(driver, 'Driver Name', 0)
            raw_route = str(driver.get('Route', ''))
            route_num = clean_num(raw_route)

            # 1. SAFETY MESSAGE
            today_str = datetime.now().strftime("%m/%d/%Y")
            safety_msg = "Perform a thorough pre-trip inspection."
            if not safety_df.empty:
                s_match = safety_df[safety_df.iloc[:, 0].astype(str).str.contains(today_str, na=False)]
                if not s_match.empty: safety_msg = s_match.iloc[0, 1]
            st.markdown(f"<div class='safety-box'><h2>⚠️ DAILY SAFETY REMINDER</h2><p>{safety_msg}</p></div>", unsafe_allow_html=True)

            # 2. CONFIRMATION TOGGLE
            is_confirmed = st.toggle("I have submitted the Confirmation Form", key=f"conf_{user_input}")
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfnw_F7nGy4GbJlMlCxSSGXx86b8g5J6VhXRkz_ZvABr2fcMg/viewform?"
            params = {"entry.534103007": d_name, "entry.726947479": user_input, "entry.316322786": raw_route}
            full_url = form_url + urllib.parse.urlencode(params)
            if not is_confirmed:
                st.markdown(f'<a href="{full_url}" target="_blank" class="btn-confirm">🚛 READ SAFETY & CONFIRM ROUTE</a>', unsafe_allow_html=True)
            else:
                st.markdown(f'<a href="{full_url}" target="_blank" class="btn-done">✅ ROUTE CONFIRMED</a>', unsafe_allow_html=True)

            # 3. DRIVER HEADER (With Name & Employee ID)
            st.markdown(f"""
                <div class='header-box'>
                    <div style='font-size:30px; font-weight:bold;'>{d_name}</div>
                    <div style='font-size:20px; opacity:0.9;'>Employee ID: <b>{user_input}</b> | Route: <b>{raw_route}</b></div>
                </div>
            """, unsafe_allow_html=True)
            
            # Compliance Cards
            dot_c, dot_m = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_c, cdl_m = get_renewal_status(driver.get('DL Expiration Date'))
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_c}<br><b style='color:red;'>{dot_m}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_c}<br><b style='color:red;'>{cdl_m}</b></small></div>", unsafe_allow_html=True)
            st.info(f"**Tenure:** {calculate_tenure(driver.get('Hire Date'))}")

            # 4. DISPATCH NOTES
            dispatch_notes_df['route_match'] = dispatch_notes_df.iloc[:, 0].apply(clean_num)
            d_info = dispatch_notes_df[dispatch_notes_df['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                t1, t2 = str(r_data.get('1st Trailer', '')), str(r_data.get('2nd Trailer', ''))
                trailers = t1 if t1 not in ('nan', '0', '') else ""
                if t2 not in ('nan', '0', ''): trailers += f" / {t2}" if trailers else t2
                st.markdown(f"<div class='dispatch-box'><h3>Dispatch Notes</h3><div style='font-size:22px; font-weight:bold; color:#d35400 !important; margin:10px 0;'>{r_data.get('Comments', 'None')}</div><div style='font-size:18px;'><b>Trailers:</b> {trailers if trailers else 'None assigned'}</div></div>", unsafe_allow_html=True)

            # 5. ELD LOGIN (High-Visibility Card)
            p_id = clean_id_alphanumeric(safe_get(driver, 'PeopleNet ID', 12))
            st.markdown(f"""
                <div class='eld-card'>
                    <div style='font-size:16px; opacity:0.8; margin-bottom:10px;'>PEOPLENET / ELD LOGIN</div>
                    <div style='display:flex; justify-content:space-around;'>
                        <div>ORG ID<br><span class='eld-val'>3299</span></div>
                        <div>DRIVER ID<br><span class='eld-val'>{p_id}</span></div>
                        <div>PASSWORD<br><span class='eld-val'>{p_id}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 6. SCHEDULE & STOP BUTTONS
            st.markdown("### Daily Schedule")
            if route_num:
                schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                my_stops = schedule[schedule['route_match'] == route_num]
                for _, stop in my_stops.iterrows():
                    sid_raw = clean_num(safe_get(stop, 'Store ID', 4))
                    sid_5 = sid_raw.zfill(5)
                    addr = safe_get(stop, 'Store Address', 5)
                    with st.expander(f"📍 Store {sid_5}", expanded=True):
                        st.markdown(f"<div class='stop-detail-card'><b>Address:</b><br>{addr}</div>", unsafe_allow_html=True)
                        
                        tracker_url = f"tel:8008710204,1,,88012#,,{sid_raw},#,,,1,,,1"
                        google_url = f"https://www.google.com/maps/search/?api=1&query={addr.replace(' ','+')}"
                        s_map_url = f"https://wg.cpcfact.com/store-{sid_5}/"
                        issue_url = f"https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u&r6db86d06117646df9723ec7f53f3e1f3={sid_5}"
                        
                        st.markdown(f"<a href='{tracker_url}' class='btn-green'>📞 Store Tracker</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{google_url}' class='btn-blue'>🌎 Google Maps</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{s_map_url}' class='btn-blue'>🗺️ Store Map</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{issue_url}' class='btn-red'>🚨 Report Issue (Feedback)</a>", unsafe_allow_html=True)
            
            st.divider()
            for _, link in quick_links.iterrows():
                n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                st.markdown(f"<a href='{v}' class='btn-blue'>{n}</a>", unsafe_allow_html=True)
        else: st.error("ID not found.")
except Exception as e: st.error(f"Error: {e}")
